import hashlib
import json
from typing import Literal
from uuid import UUID
from pydantic import AwareDatetime, BaseModel, ConfigDict
from api.contracts import Claim


class ClaimEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_version: Literal[1] = 1
    event_type: Literal['claim.created'] = 'claim.created'
    event_id: UUID
    occurred_at: AwareDatetime
    claim: Claim

    def canonical(self):
        return json.dumps(self.model_dump(mode='json'), sort_keys=True, separators=(',', ':'))

    def digest(self):
        return hashlib.sha256(self.canonical().encode()).hexdigest()
