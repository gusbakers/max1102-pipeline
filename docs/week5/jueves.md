# Jueves — Piloto de ingesta con Kafka

## Bloque 1. Entender el alcance

El productor genera eventos sintéticos `claim.created`, Kafka los almacena en `claims.events.v1` y el consumidor los valida y guarda en PostgreSQL. Cada evento incluye versión de esquema, UUID de evento, fecha/hora con zona y un claim que utiliza el contrato compartido de la API.

La clave de Kafka es `claim_id`. El piloto usa una partición y un broker KRaft; no exige ZooKeeper. Esta configuración verifica el flujo, pero no ofrece alta disponibilidad ni mide la capacidad de un clúster empresarial.

## Bloque 2. Publicar y consumir

Carga `week5/.env` y comprueba que el Compose de Week 5 está iniciado. Desde la raíz:

```bash
.venv-week5/bin/python -m streaming.producer --count 20 --interval 0.25
.venv-week5/bin/python -m streaming.consumer --max-messages 20
```

El productor crea el topic si no existe y exige confirmación del broker. El consumidor del ejemplo termina al procesar 20 mensajes. Para seguir escuchando usa `--max-messages 0`; el timeout de inactividad inicial es 60 segundos. `--idle-timeout 0` mantiene la escucha indefinida. Ctrl+C detiene el proceso y conserva los offsets confirmados.

Si utilizaste antes el mismo grupo, recuerda que reanuda desde sus offsets guardados. El número indicado es de mensajes consumidos, no necesariamente filas nuevas. Para consultar la recepción y los rechazos sin instalar psql en Codespaces:

```bash
docker compose --env-file week5/.env -f compose.week5.yml exec knowledge-db \
  psql -U max_week5 -d max_week5 -c 'SELECT count(*) FROM week5_stream.events;'
docker compose --env-file week5/.env -f compose.week5.yml exec knowledge-db \
  psql -U max_week5 -d max_week5 -c 'SELECT reason, count(*) FROM week5_stream.rejections GROUP BY reason;'
```

## Bloque 3. Saber qué garantiza

La entrega es **al menos una vez**. El consumidor realiza primero la transacción de PostgreSQL y confirma después el offset en Kafka. Si se interrumpe entre ambos pasos, el mensaje reaparece; el UUID y hash del evento evitan una segunda fila.

Un mismo ID con contenido diferente se registra como conflicto. Mensajes mal formados o con clave incompatible se guardan como rechazos identificados por topic, partición y offset, con hash del mensaje. No hay un topic DLQ adicional: la cuarentena del piloto es esa tabla. Si falla PostgreSQL, no se confirma el offset y el proceso falla para que se pueda reintentar.

No se afirma exactamente una vez entre Kafka y PostgreSQL. Tampoco se deduce que el reporte mensual o el RAG se actualicen automáticamente: conectar la tabla de eventos con Delta o con el índice requiere otro consumidor o proceso de publicación.

## Bloque 4. Evaluar y apagar

El viernes se comprueban reinicio del consumidor, repetición desde el comienzo, IDs conflictivos, JSON inválido y claves incompatibles. Para una observación operativa, consulta el grupo:

```bash
docker compose --env-file week5/.env -f compose.week5.yml exec kafka \
  /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group claims-pilot-v1
```

El lag indica mensajes pendientes respecto al final del topic. No equivale por sí solo a latencia en segundos. Para medir tiempo de llegada compara `occurred_at` con `received_at` en PostgreSQL, teniendo en cuenta que este productor y consumidor comparten el reloj del laboratorio.

`week5/sql/002_monitor.sql` incluye consultas de conteo, tiempo medio/p95 observado, rechazos e inventario de colecciones. Ejecútalo con psql conectado a la base del piloto; no son métricas de rendimiento medidas durante la implementación.

Para detener los servicios conservando datos y offsets:

```bash
docker compose --env-file week5/.env -f compose.week5.yml down
```

Después detén Codespaces. El volumen de PostgreSQL y el de Kafka se conservan. El comando `down -v` los elimina; solo se usa automáticamente en los runners desechables de CI.
