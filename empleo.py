"""Búsqueda, filtrado, redacción y envío de candidaturas (con aprobación manual).

Uso:
  python empleo.py buscar            # Adzuna + alertas de email -> filtra -> redacta borradores
  python empleo.py enviar_todo       # Envía de forma automática todas las ofertas nuevas con email
  python empleo.py auto              # Busca, filtra, redacta y envía automáticamente las que tengan email
  python empleo.py panel             # abre el panel en http://127.0.0.1:8765
  python empleo.py empresas f.csv    # importa empresas (nombre,email,web) para contacto directo
"""
import csv, email, imaplib, json, random, re, smtplib, sqlite3, ssl, sys, time
import urllib.parse, urllib.request, webbrowser
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import config as C

# ---------- base de datos ----------
def db():
    con = sqlite3.connect(C.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS ofertas(
        id TEXT PRIMARY KEY, titulo TEXT, empresa TEXT, url TEXT, descripcion TEXT,
        fuente TEXT, score INTEGER, estado TEXT DEFAULT 'nueva', borrador TEXT,
        destino TEXT, creada TEXT, enviada TEXT)""")
    return con

def guardar(con, o):
    if con.execute("SELECT 1 FROM ofertas WHERE id=?", (o["id"],)).fetchone():
        return False
    con.execute("""INSERT INTO ofertas(id,titulo,empresa,url,descripcion,fuente,score,destino,creada)
                   VALUES(:id,:titulo,:empresa,:url,:descripcion,:fuente,:score,:destino,:creada)""", o)
    return True

# ---------- utilidades ----------
def http_json(url, datos=None, cabeceras=None, timeout=60):
    req = urllib.request.Request(
        url, data=None if datos is None else json.dumps(datos).encode(),
        headers={"Content-Type": "application/json", **(cabeceras or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

RE_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
def puntuar(titulo, desc):
    t, d = titulo.lower(), (desc or "").lower()
    s = sum(2 for k in C.SUMA if k in t) + sum(1 for k in C.SUMA if k in d)
    s -= 3 * sum(k in t for k in C.RESTA) + 2 * sum(k in d for k in C.RESTA)
    return s

def nueva_oferta(id_, titulo, empresa, url, desc, fuente, destino=""):
    if not destino:
        m = RE_MAIL.search(desc or "")
        destino = m.group(0) if m else ""
    return dict(id=id_, titulo=titulo, empresa=empresa, url=url, descripcion=(desc or "")[:2000],
                fuente=fuente, score=puntuar(titulo, desc), destino=destino,
                creada=datetime.now().isoformat(timespec="seconds"))

# ---------- fuentes ----------
def de_adzuna():
    if not C.ADZUNA_ID:
        print("· Adzuna: falta ADZUNA_ID/ADZUNA_KEY (se omite)"); return []
    out = []
    for q in C.BUSQUEDAS:
        p = urllib.parse.urlencode(dict(app_id=C.ADZUNA_ID, app_key=C.ADZUNA_KEY, what=q,
            where="Madrid", distance=15, results_per_page=30, sort_by="date", max_days_old=14))
        try:
            r = http_json(f"https://api.adzuna.com/v1/api/jobs/es/search/1?{p}")
        except Exception as e:
            print(f"· Adzuna '{q}': {e}"); continue
        
        for x in r.get("results", []):
            loc = x.get("location", {})
            loc_nombre = loc.get("display_name", "").lower()
            
            # FILTRO ESTRICTO: Solo aceptar si la ubicación contiene "madrid"
            if "madrid" not in loc_nombre:
                continue
                
            out.append(nueva_oferta("adzuna:" + str(x["id"]), x["title"],
                x.get("company", {}).get("display_name", ""), x["redirect_url"],
                x.get("description", ""), "adzuna"))
        time.sleep(1)
    return out

def de_alertas_email():
    if not C.GMAIL_APP_PASSWORD:
        print("· Alertas email: falta GMAIL_APP_PASSWORD (se omite)"); return []
    out, desde = [], (date.today() - timedelta(days=14)).strftime("%d-%b-%Y")
    try:
        m = imaplib.IMAP4_SSL("imap.gmail.com")
        m.login(C.GMAIL_USER, C.GMAIL_APP_PASSWORD); m.select("INBOX", readonly=True)
        for rem in C.REMITENTES_ALERTAS:
            _, ids = m.search(None, f'(SINCE "{desde}" FROM "{rem}")')
            for i in ids[0].split()[-30:]:
                _, dat = m.fetch(i, "(BODY.PEEK[])")
                msg = email.message_from_bytes(dat[0][1])
                for parte in msg.walk():
                    if parte.get_content_type() != "text/html": continue
                    html = parte.get_payload(decode=True).decode(parte.get_content_charset() or "utf-8", "ignore")
                    for href, txt in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
                        txt = re.sub(r"<[^>]+>|\s+", " ", txt).strip()
                        if len(txt) > 8 and any(p in href for p in C.PATRONES_ENLACE):
                            out.append(nueva_oferta("mail:" + href.split("?")[0][-80:], txt[:120],
                                       "", href, "", f"alerta {rem}"))
        m.logout()
    except Exception as e:
        print(f"· Alertas email: {e}")
    return out

def de_csv_empresas(ruta):
    out = []
    for f in csv.DictReader(open(ruta, encoding="utf-8")):
        out.append(nueva_oferta("emp:" + f["email"], "Candidatura espontánea: prácticas Data Engineer / Consultoría",
                   f["nombre"], f.get("web", ""), "prácticas data engineer", "empresa", f["email"]))
        out[-1]["score"] = 99
    return out

# ---------- redacción ----------
def prompt(o):
    return f"""Redacta un email de candidatura en español, de 110 a 150 palabras, cercano y profesional.
Usa SOLO estos datos del candidato, sin inventar nada:
{C.PERFIL}

Oferta: {o['titulo']} · Empresa: {o['empresa'] or 'desconocida'}
Descripción: {o['descripcion'][:1200] or '(sin descripción: candidatura espontánea)'}

Conecta 2-3 puntos concretos del perfil con lo que pide la oferta. Menciona que adjunta el CV.
Termina con "Un saludo, Jaime Perán". Devuelve solo el cuerpo del email, sin asunto ni comillas."""

def plantilla(o):
    return (f"Hola,\n\nSoy Jaime Perán, Técnico Superior en DAM y estudiante del Máster en Big Data e IA. "
            f"Me interesa la posición «{o['titulo']}»{' en ' + o['empresa'] if o['empresa'] else ''}. "
            "He hecho prácticas en Atos desarrollando aplicaciones en equipos ágiles y he trabajado en un "
            "pipeline con Python, Spark y Databricks. Adjunto mi CV; estoy disponible por las mañanas.\n\n"
            "Un saludo,\nJaime Perán")

def redactar(o):
    try:
        if C.GEMINI_KEY:
            r = http_json(f"https://generativelanguage.googleapis.com/v1beta/models/{C.GEMINI_MODEL}:generateContent",
                {"contents": [{"parts": [{"text": prompt(o)}]}]}, {"x-goog-api-key": C.GEMINI_KEY})
            txt = r["candidates"][0]["content"]["parts"][0]["text"]
        else:
            txt = http_json("http://localhost:11434/api/generate",
                {"model": C.OLLAMA_MODEL, "prompt": prompt(o), "stream": False}, timeout=180)["response"]
    except Exception as e:
        print(f"  (sin IA: {e}); uso plantilla"); txt = plantilla(o)
    pie = "\n\n—\nSi no desea recibir más comunicaciones, basta con que me lo indique." if o["fuente"] == "empresa" else ""
    return txt.strip() + pie

# ---------- envío ----------
def enviados_hoy(con):
    return con.execute("SELECT COUNT(*) FROM ofertas WHERE enviada LIKE ?", (date.today().isoformat() + "%",)).fetchone()[0]

def enviar(con, id_):
    o = con.execute("SELECT * FROM ofertas WHERE id=?", (id_,)).fetchone()
    if not o or not o["destino"]: return "Esta oferta no tiene email de destino: aplica desde su web."
    if o["estado"] == "enviada": return "Ya enviada."
    if enviados_hoy(con) >= C.MAX_DIARIO: return f"Límite diario alcanzado ({C.MAX_DIARIO})."
    if not C.GMAIL_APP_PASSWORD or not C.CV_PDF.exists(): return "Falta GMAIL_APP_PASSWORD o el PDF del CV."
    
    m = EmailMessage()
    m["From"], m["To"] = f"Jaime Perán <{C.GMAIL_USER}>", o["destino"]
    m["Subject"] = f"Candidatura: {o['titulo'][:80]} – Jaime Perán"
    m.set_content(o["borrador"])
    m.add_attachment(C.CV_PDF.read_bytes(), maintype="application", subtype="pdf",
                     filename="CV_Jaime_Peran_Alcantarilla.pdf")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(C.GMAIL_USER, C.GMAIL_APP_PASSWORD); s.send_message(m)
    
    fecha_envio = datetime.now().isoformat(timespec="seconds")
    con.execute("UPDATE ofertas SET estado='enviada', enviada=? WHERE id=?", (fecha_envio, id_))
    con.commit()
    
    # --- REGISTRO AUTOMÁTICO EN ARCHIVO CSV ---
    with open("historial_enviados.csv", "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([o['empresa'] or 'Desconocida', o['titulo'], o['destino'], fecha_envio])
        
    time.sleep(random.uniform(2, 6))
    return "ok"

def enviar_masivo():
    con = db()
    pendientes = con.execute(
        "SELECT id, titulo, empresa, destino FROM ofertas WHERE estado='nueva' AND destino != '' ORDER BY score DESC"
    ).fetchall()
    
    if not pendientes:
        print("No hay ofertas nuevas con correo electrónico de destino para enviar.")
        return

    print(f"Encontradas {len(pendientes)} ofertas con email listas para enviar (límite diario: {C.MAX_DIARIO})...")
    enviadas = 0
    for o in pendientes:
        res = enviar(con, o["id"])
        if res == "ok":
            enviadas += 1
            print(f"  [OK] Enviada a {o['destino']} ({o['empresa']} - {o['titulo'][:40]})")
        elif "Límite diario" in res:
            print(f"  [STOP] {res}")
            break
        else:
            print(f"  [ERROR] {o['titulo'][:40]}: {res}")
    print(f"\nProceso terminado. Total enviadas hoy: {enviadas}")

# ---------- flujo ----------
def procesar(ofertas):
    con = db(); nuevas = 0
    for o in sorted(ofertas, key=lambda x: -x["score"]):
        if o["score"] < C.MIN_SCORE or not guardar(con, o): continue
        print(f"+ [{o['score']:>2}] {o['titulo'][:70]} · {o['empresa']}")
        con.execute("UPDATE ofertas SET borrador=? WHERE id=?", (redactar(o), o["id"])); con.commit(); nuevas += 1
    print(f"\n{nuevas} ofertas nuevas. Revísalas con: python empleo.py panel")

# ---------- panel web ----------
class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith("/api/ofertas"):
            con = db(); rows = [dict(r) for r in con.execute("SELECT * FROM ofertas ORDER BY score DESC, creada DESC")]
            return self._json({"ofertas": rows, "hoy": enviados_hoy(con), "max": C.MAX_DIARIO})
        b = (C.BASE / "panel.html").read_bytes()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_POST(self):
        if self.headers.get("Origin", "").replace("http://", "") not in ("", f"127.0.0.1:{C.PUERTO}", f"localhost:{C.PUERTO}"):
            return self._json({"error": "origen no permitido"}, 403)
        d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        con = db()
        if self.path == "/api/guardar":
            con.execute("UPDATE ofertas SET borrador=?, destino=?, estado=? WHERE id=?",
                        (d["borrador"], d["destino"], d["estado"], d["id"])); con.commit(); return self._json({"ok": True})
        if self.path == "/api/enviar":
            con.execute("UPDATE ofertas SET borrador=?, destino=? WHERE id=?", (d["borrador"], d["destino"], d["id"]))
            con.commit()
            try: res = enviar(con, d["id"])
            except Exception as e: res = f"Error SMTP: {e}"
            return self._json({"resultado": res})
        self._json({"error": "ruta"}, 404)
    def log_message(self, *a): pass

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "panel"
    if cmd == "buscar": procesar(de_adzuna() + de_alertas_email())
    elif cmd == "enviar_todo": enviar_masivo()
    elif cmd == "auto":
        procesar(de_adzuna() + de_alertas_email())
        enviar_masivo()
    elif cmd == "empresas": procesar(de_csv_empresas(sys.argv[2]))
    elif cmd == "panel":
        s = ThreadingHTTPServer(("127.0.0.1", C.PUERTO), H)
        print(f"Panel en http://127.0.0.1:{C.PUERTO}  (Ctrl+C para salir)")
        webbrowser.open(f"http://127.0.0.1:{C.PUERTO}"); s.serve_forever()
    else: print(__doc__)

if __name__ == "__main__":
    main()
