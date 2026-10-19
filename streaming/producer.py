"""Publish bounded synthetic events and require broker acknowledgements."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
import time
from uuid import uuid4

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from streaming.events import ClaimEvent

TOPIC = 'claims.events.v1'


def ensure_topic(bootstrap, topic=TOPIC):
    admin = AdminClient({'bootstrap.servers': bootstrap, 'socket.timeout.ms': 10000})
    future = admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)])[topic]
    try:
        future.result(timeout=20)
    except Exception as exc:
        from confluent_kafka import KafkaError, KafkaException
        if not isinstance(exc, KafkaException) or exc.args[0].code() != KafkaError.TOPIC_ALREADY_EXISTS:
            raise


def publish(events, bootstrap, topic=TOPIC, interval=0):
    producer = Producer({'bootstrap.servers': bootstrap, 'enable.idempotence': True,
                         'acks': 'all', 'delivery.timeout.ms': 30000})
    failures = []
    def delivered(error, message):
        if error:
            failures.append(error.code())
    count = 0
    for event in events:
        producer.produce(topic, key=event.claim.claim_id.encode(), value=event.canonical().encode(),
                         on_delivery=delivered)
        producer.poll(0)
        count += 1
        if interval:
            time.sleep(interval)
    pending = producer.flush(35)
    if failures or pending:
        raise RuntimeError('Some events were not acknowledged by Kafka')
    return count


def synthetic_events(count):
    for index in range(count):
        now = datetime.now(timezone.utc)
        yield ClaimEvent(event_id=uuid4(), occurred_at=now, claim={
            'claim_id': f'PILOT-{index:05d}', 'claim_amount': Decimal('100.00') + index,
            'claim_status': ['PAID', 'DENIED', 'PENDING'][index % 3], 'service_date': now.date()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--interval', type=float, default=0.25)
    args = parser.parse_args()
    if not 1 <= args.count <= 10000 or not 0 <= args.interval <= 10:
        parser.error('Use count 1..10000 and interval 0..10')
    bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    ensure_topic(bootstrap)
    print(json.dumps({'acknowledged': publish(synthetic_events(args.count), bootstrap, interval=args.interval)}))
