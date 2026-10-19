"""At-least-once consumption; durable DB transaction precedes offset commit."""
import argparse
import hashlib
import json
import os
import signal
import time

from confluent_kafka import Consumer, KafkaException
import psycopg
from psycopg.types.json import Jsonb
from pydantic import ValidationError
from streaming.events import ClaimEvent
from streaming.producer import TOPIC


def persist_record(database_url, value, key, topic, partition, offset):
    raw = value or b''
    reason, event = None, None
    try:
        if not raw or len(raw) > 65536:
            reason = 'EMPTY_OR_OVERSIZED_MESSAGE'
        else:
            event = ClaimEvent.model_validate_json(raw)
            if key != event.claim.claim_id.encode():
                reason = 'KEY_MISMATCH'
    except (ValidationError, ValueError):
        reason = 'INVALID_EVENT_SCHEMA'
    with psycopg.connect(database_url, connect_timeout=5,
                         options='-c statement_timeout=5000') as conn:
        outcome = 'rejected'
        if reason is None:
            digest = event.digest()
            inserted = conn.execute('''INSERT INTO week5_stream.events
                (event_id, claim_id, occurred_at, payload, payload_hash)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (event_id) DO NOTHING RETURNING event_id''',
                (event.event_id, event.claim.claim_id, event.occurred_at,
                 Jsonb(event.model_dump(mode='json')), digest)).fetchone()
            if inserted:
                outcome = 'inserted'
            else:
                existing = conn.execute('SELECT payload_hash FROM week5_stream.events WHERE event_id=%s',
                                        (event.event_id,)).fetchone()
                if existing[0] != digest:
                    reason = 'EVENT_ID_CONFLICT'
                else:
                    outcome = 'duplicate'
        if reason:
            conn.execute('''INSERT INTO week5_stream.rejections
                (topic, partition_id, offset_id, reason, payload_hash) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (topic, partition_id, offset_id) DO NOTHING''',
                (topic, partition, offset, reason, hashlib.sha256(raw).hexdigest()))
    # Exiting the context committed the database transaction successfully.
    return outcome


def consume(database_url, bootstrap, group, topic=TOPIC, max_messages=0, idle_timeout=60):
    consumer = Consumer({'bootstrap.servers': bootstrap, 'group.id': group,
        'enable.auto.commit': False, 'enable.auto.offset.store': False,
        'auto.offset.reset': 'earliest', 'max.poll.interval.ms': 120000})
    counts = {'inserted': 0, 'duplicate': 0, 'rejected': 0}
    last_message = time.monotonic()
    try:
        consumer.subscribe([topic])
        while not max_messages or sum(counts.values()) < max_messages:
            message = consumer.poll(1)
            if message is None:
                if idle_timeout and time.monotonic() - last_message > idle_timeout:
                    if max_messages:
                        raise TimeoutError('Expected messages were not received')
                    break
                continue
            if message.error():
                raise KafkaException(message.error())
            outcome = persist_record(database_url, message.value(), message.key(), message.topic(),
                                     message.partition(), message.offset())
            # If the process dies before this commit, the database deduplicates redelivery.
            consumer.commit(message=message, asynchronous=False)
            counts[outcome] += 1
            last_message = time.monotonic()
    finally:
        consumer.close()
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-messages', type=int, default=0)
    parser.add_argument('--idle-timeout', type=int, default=60)
    args = parser.parse_args()
    if args.max_messages < 0 or args.idle_timeout < 0:
        parser.error('Message count and idle timeout must be nonnegative')
    database = os.getenv('STREAM_DATABASE_URL', '')
    if not database:
        parser.error('Set STREAM_DATABASE_URL')
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        print(json.dumps(consume(database, os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            os.getenv('KAFKA_GROUP_ID', 'claims-pilot-v1'), max_messages=args.max_messages,
            idle_timeout=args.idle_timeout)))
    except KeyboardInterrupt:
        print('Consumer stopped; committed offsets are preserved.')
    except Exception as exc:
        raise SystemExit(f'Consumer failed ({type(exc).__name__}); uncommitted messages can be retried.') from None
