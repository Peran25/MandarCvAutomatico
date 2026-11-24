"""Configuración. Los secretos van en .env (copia .env.example)."""
import os
from pathlib import Path

BASE = Path(__file__).parent
_env = BASE / ".env"
if _env.exists():
    for linea in _env.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.strip().startswith("#"):
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

G = os.environ.get
GMAIL_USER = G("GMAIL_USER", "jaimeperan3@gmail.com")
GMAIL_APP_PASSWORD = G("GMAIL_APP_PASSWORD", "")      # contraseña de aplicación
ADZUNA_ID, ADZUNA_KEY = G("ADZUNA_ID", ""), G("ADZUNA_KEY", "")
GEMINI_KEY, GEMINI_MODEL = G("GEMINI_API_KEY", ""), G("GEMINI_MODEL", "gemini-2.5-flash")
OLLAMA_MODEL = G("OLLAMA_MODEL", "gemma3:4b")
CV_PDF = BASE / "CV_Jaime_Peran_Alcantarilla.pdf"
DB_PATH = BASE / "candidaturas.db"
MAX_DIARIO = int(G("MAX_DIARIO", "15"))                # tope de emails por día
MIN_SCORE = int(G("MIN_SCORE", "3"))
PUERTO = int(G("PUERTO", "8765"))

BUSQUEDAS = [
    "data engineer prácticas", "becario big data", "junior data engineer",
    "consultor tecnológico junior", "prácticas desarrollador multiplataforma",
    "técnico sistemas microinformáticos", "becario cloud aws", "junior python spark",
]
SUMA = ["prácticas", "practicas", "becario", "beca", "junior", "trainee", "data engineer",
        "big data", "spark", "databricks", "python", "sql", "cloud", "aws", "consultor",
        "power bi", "java", "kotlin", "c#", "sistemas", "soporte", "linux"]
RESTA = ["senior", "sr.", "lead", "responsable", "director", "5 años", "4 años",
         "3 años", "comercial", "ventas", "teleoperador"]

# Alertas por email (LinkedIn, InfoJobs, Indeed, Tecnoempleo)
REMITENTES_ALERTAS = ["linkedin.com", "infojobs.net", "indeed.com", "tecnoempleo.com"]
PATRONES_ENLACE = ["/jobs/view", "infojobs.net/oferta", "indeed.com/viewjob",
                   "indeed.com/rc/clk", "tecnoempleo.com/"]

PERFIL = """Jaime Perán Alcantarilla, Madrid. Técnico Superior en DAM (2026) y Técnico en SMR.
Cursa el Máster en Big Data e Inteligencia Artificial (tardes/online). AWS Academy Graduate (2024).
Prácticas en Atos (mar–jun 2026): desarrollo de aplicaciones multiplataforma con patrones de diseño,
equipos ágiles en entorno multinacional. Proyecto del máster: pipeline de ingesta y transformación
con Python, Apache Spark y Databricks. Skills: Python, Spark, Databricks, Power BI, SQL, Oracle,
AWS, Linux/Windows, redes, Java, C#, Kotlin, Git. Español nativo, inglés intermedio.
Busca beca/prácticas como Data Engineer o Consultor Tecnológico en Madrid, disponible por las mañanas.
Contacto: jaimeperan3@gmail.com · 683 41 87 04."""
