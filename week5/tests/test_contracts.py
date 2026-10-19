from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import pytest
from pydantic import ValidationError
from streaming.events import ClaimEvent
from week5.ingest_knowledge import chunks_from_file


def test_event_requires_timezone_and_shared_claim_contract():
    event = dict(event_id=uuid4(), occurred_at=datetime.now(timezone.utc), claim={
        'claim_id':'C1', 'claim_amount':100, 'claim_status':'PENDING', 'service_date':'2025-12-10'})
    assert ClaimEvent(**event).digest() == ClaimEvent(**event).digest()
    for update in [{'occurred_at':'2025-12-10T12:00:00'}, {'schema_version':2},
                   {'claim':event['claim'] | {'claim_amount':-1}}, {'extra':'forbidden'}]:
        with pytest.raises(ValidationError):
            ClaimEvent(**(event | update))


def test_corpus_ids_are_stable_and_chunks_bounded():
    root = Path(__file__).resolve().parents[2]
    chunks = chunks_from_file(root / 'knowledge/claims_reference.jsonl')
    assert len(chunks) == 5 and chunks == chunks_from_file(root / 'knowledge/claims_reference.jsonl')
    assert all(0 < len(c['content']) <= 1050 for c in chunks)


def test_empty_corpus_cannot_delete_index(tmp_path):
    path = tmp_path / 'empty.jsonl'
    path.write_text('')
    with pytest.raises(ValueError, match='empty collection'):
        chunks_from_file(path)
