# Automatización de candidaturas (Madrid · Data Engineer / Consultor)

Herramienta en Python (librería estándar, 3.9+) para buscar ofertas de empleo y prácticas en Madrid, puntuarlas según palabras clave, generar borradores de candidatura con Gemini u Ollama (con plantilla de respaldo) y gestionar/enviar correos con CV adjunto desde un panel web local o por CLI.

## Requisitos previos

- Python 3.9 o superior.
- Tu CV en PDF en la raíz del proyecto llamado `CV_Jaime_Peran_Alcantarilla.pdf` (excluido de Git mediante `.gitignore`).

## Configuración

1. Crea tu archivo `.env` a partir de la plantilla:
   - En Linux/macOS: `cp .env.example .env`
   - En Windows (PowerShell): `Copy-Item .env.example .env`
2. Rellena en `.env` tus credenciales y ajustes:
   - `GMAIL_USER` y `GMAIL_APP_PASSWORD` (contraseña de aplicación de Gmail para envío SMTP y lectura de alertas IMAP).
   - `ADZUNA_ID` y `ADZUNA_KEY` (búsqueda en Adzuna filtrada a Madrid).
   - `GEMINI_API_KEY` y `GEMINI_MODEL` (opcional; si no hay clave de Gemini, intentará usar Ollama en `http://localhost:11434` con `OLLAMA_MODEL` y, si falla, usará una plantilla).
   - `MAX_DIARIO` (límite diario de envíos por correo, por defecto `15`) y `UBICACION`.

## Uso

- `python empleo.py buscar` → descarga ofertas (Adzuna y alertas de correo), las puntúa, guarda las que superan el umbral y genera borradores.
- `python empleo.py panel` → abre el panel web en `http://127.0.0.1:8765` para revisar, editar, copiar, marcar como aplicada/descartada o enviar con el CV adjunto.
- `python empleo.py enviar_todo` → envía de forma automática las ofertas nuevas con email de destino respetando `MAX_DIARIO`.
- `python empleo.py auto` → ejecuta `buscar` y a continuación `enviar_todo`.
- `python empleo.py empresas empresas.csv` → importa contactos directos desde un CSV con columnas `nombre,email,web`.

Los datos locales (`candidaturas.db`, `historial_enviados.csv`, `.env` y el PDF del CV) se mantienen fuera del control de versiones.

## Automatización diaria

Puedes programar `python empleo.py buscar` (o `auto`) una vez al día con **cron** (Linux/macOS) o el **Programador de tareas** de Windows.