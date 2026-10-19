# Miércoles — RAG en la API

## Bloque 1. Arrancar el servicio

Carga `week5/.env`, verifica que indexaste la colección y ejecuta desde la raíz:

```bash
.venv-week5/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

Abre el puerto 8000 de Codespaces y añade `/docs`. Autoriza con el `APP_API_KEY` local. La clave de la aplicación y la clave de Gemini tienen funciones distintas: una protege tu endpoint y la otra permite llamar al proveedor.

## Bloque 2. Probar el endpoint

`POST /claims/rag-summary` exige los mismos campos de claim que la API anterior y acepta una pregunta opcional de hasta 500 caracteres:

```json
{
  "claim_id": "DEMO-001",
  "claim_amount": 125,
  "claim_status": "PENDING",
  "service_date": "2025-12-10",
  "question": "¿Qué significa PENDING en este proyecto?"
}
```

FastAPI valida autenticación y JSON antes de llamar a Gemini. Luego se obtiene el embedding de la consulta, se recuperan documentos en pgvector y se envían al generador como contexto. El generador debe devolver una explicación estructurada con citas. El servidor comprueba que los IDs de las citas existen y que las citas textuales aparecen exactamente en los fragmentos recuperados.

La respuesta incluye `claim_id`, `summary`, `model`, `retrieval_status` y `sources`. Los valores básicos de monto, estado y fecha se formatean con código. La explicación sigue siendo una salida de LLM: tener una cita textual válida no demuestra por sí solo que cada inferencia sea correcta. La demo debe comprobar también la coherencia de la respuesta.

Cuando no hay fragmentos por encima del umbral, no se llama al generador. Si el modelo reconoce que los documentos no responden la pregunta, también se devuelve `insufficient_context`. Una cita inventada o una salida incompleta devuelve 502. Una base inaccesible devuelve 503. Un timeout devuelve 504 y una cuota agotada, 429. No se devuelve al cliente la cadena de conexión ni los detalles privados del proveedor.

## Bloque 3. Convertir el endpoint anterior

`POST /claims/llm-summary` utiliza RAG cuando `RAG_ENABLED=true`. El archivo generado para el laboratorio ya activa esa variable. Sin ella, conserva el comportamiento de resumen de Week 2 para que un despliegue sin base vectorial no quede inutilizado. `/claims/rag-summary` siempre exige RAG y nunca cae silenciosamente al resumen sin contexto.

El modelo generativo se elige con `GEMINI_MODEL`; el valor inicial nuevo es `gemini-3.5-flash-lite`. El modelo de embeddings es `gemini-embedding-001`, con contrato fijo de 768 dimensiones. Cambiar de modelo de embeddings requiere reindexar y actualizar su adaptador, no cambiar solo un nombre.

Prueba automática contra tu servidor:

```bash
.venv-week5/bin/python -m week5.smoke_rag
```

El script comprueba `/rag/health`, envía un claim sintético y exige contexto usado y fuentes. Guarda un registro sin claves en `week5/evidence/rag-smoke.json`. `/health` comprueba HTTP y `/rag/health` comprueba colección y conexión; ninguno certifica por sí solo la disponibilidad de Gemini.

## Bloque 4. Activar en Azure

El ZIP de la API ahora incluye los módulos del RAG y su contrato compartido. El workflow de Week 4 sigue usando sus reglas de activación y exige las pruebas de Week 5 antes del CD.

Para que el RAG responda en Azure, configura allí `GEMINI_API_KEY`, `GEMINI_MODEL`, `APP_API_KEY`, `RAG_DATABASE_URL`, `RAG_COLLECTION`, `RAG_MIN_SIMILARITY`, `RAG_TOP_K` y `RAG_ENABLED=true`. La URL de PostgreSQL debe apuntar a una base persistente accesible desde Azure, con pgvector, el esquema SQL de `week5/sql/001_init.sql` y la colección indexada. Usa SSL en esa conexión según el proveedor.

La dirección `localhost:5433` del Codespace no sirve para Azure. Un Codespace detenido tampoco aloja una base permanente. Esta entrega no contrata un PostgreSQL administrado ni copia las claves del laboratorio a Azure. Cuando exista esa conexión, ejecuta el smoke con `--url https://maxweek2-gusbakers-972358cb.azurewebsites.net`, usando el APP_API_KEY de Azure, y conserva el resultado como evidencia del despliegue real.
