# Martes — Corpus, embeddings y búsqueda semántica

## Bloque 1. Definir la fuente de contexto

`knowledge/claims_reference.jsonl` contiene cinco documentos versionados que describen estados, reglas de calidad y alcance del proyecto. No se presentan como políticas de una aseguradora. Cada documento tiene `source`, `title` y `text`. El campo source permite rastrear la información que aparece en una respuesta.

El corpus inicial no contiene información personal ni filas individuales de claims. Las tablas curadas de dbt son un flujo distinto. Una futura incorporación de datos de negocio al corpus necesita un extractor y reglas de actualización explícitas; no ocurre automáticamente por tener dbt.

## Bloque 2. Indexar

Con PostgreSQL iniciado y las variables de `week5/.env` cargadas, ejecuta:

```bash
.venv-week5/bin/python -m week5.ingest_knowledge
```

El script divide textos largos en fragmentos de hasta 1.050 caracteres con solapamiento. Genera IDs estables y hashes del contenido. Para cada fragmento nuevo llama a `gemini-embedding-001` con tarea `RETRIEVAL_DOCUMENT` y 768 dimensiones. Normaliza el vector y lo guarda en `week5_knowledge.chunks` junto con su fuente y modelo.

El indexado necesita una clave de Gemini válida y cuota para embeddings. Repetirlo reutiliza los embeddings de fragmentos sin cambios. Si falla una llamada, la colección existente se conserva. La sustitución de la colección ocurre en una sola transacción después de obtener todos los vectores; elimina también documentos retirados del archivo.

## Bloque 3. Entender la búsqueda

Una consulta usa el mismo modelo y dimensiones, con tarea `RETRIEVAL_QUERY`. PostgreSQL calcula similitud coseno y devuelve hasta `RAG_TOP_K` fragmentos de la colección y modelo configurados, por encima de `RAG_MIN_SIMILARITY`.

El piloto usa búsqueda exacta. Con cinco documentos no necesita un índice aproximado HNSW ni afirma mejoras de rendimiento inexistentes. Colecciones o modelos distintos no se mezclan. Los parámetros SQL se envían por separado, no se concatenan con la pregunta.

## Bloque 4. Medir antes de afirmar calidad

```bash
.venv-week5/bin/python -m week5.evaluate_retrieval
```

La evaluación usa las cinco preguntas etiquetadas de `knowledge/retrieval_cases.jsonl` y guarda `week5/evidence/retrieval.json`. Informa hit@k con las llamadas reales de tu cuenta. Un resultado de 5/5 en este pequeño conjunto solo acredita esos casos. El umbral inicial 0,55 no se presenta como calibrado; revisa qué fuentes recupera, amplía los casos y ajusta el umbral con evidencia.

Las pruebas automáticas de integración usan vectores deterministas y verifican la mecánica de SQL, aislamiento, reindexado y errores. No miden la calidad semántica de Gemini real.
