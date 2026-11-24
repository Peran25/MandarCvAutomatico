# Automatización de candidaturas (Madrid · Data Engineer / Consultor)

1. `cp .env.example .env` y rellénalo (Gmail con contraseña de aplicación, claves de Adzuna y Gemini; sin Gemini usa Ollama).
2. `python empleo.py buscar` → descarga ofertas, las puntúa, descarta las que no encajan y redacta un borrador.
3. `python empleo.py panel` → revisas, editas y envías (o marcas "ya apliqué").
4. Contacto directo: `python empleo.py empresas empresas.csv` (columnas `nombre,email,web`).

Solo usa la librería estándar de Python (3.9+). Tope diario configurable (`MAX_DIARIO`).
Programa `buscar` una vez al día con cron / Programador de tareas.
