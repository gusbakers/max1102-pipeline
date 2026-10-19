"""Authenticated smoke request without printing credentials or the claim payload."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.username or url.password or url.query or url.fragment or url.path not in {'','/'}:
        parser.error('Use a plain server origin without a path or credentials')
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in {'localhost','127.0.0.1'}):
        parser.error('Use HTTPS or local HTTP')
    key = os.getenv('APP_API_KEY', '')
    if not key:
        parser.error('Set APP_API_KEY')
    with httpx.Client(timeout=50) as client:
        ready = client.get(args.url.rstrip('/')+'/rag/health', headers={'X-API-Key':key})
        ready.raise_for_status()
        result = client.post(args.url.rstrip('/')+'/claims/rag-summary', headers={'X-API-Key':key}, json={
            'claim_id':'SMOKE-SYNTHETIC', 'claim_amount':125, 'claim_status':'PENDING',
            'service_date':'2025-12-10', 'question':'¿Qué significa PENDING en el proyecto?'})
        result.raise_for_status()
        body = result.json()
        if body['retrieval_status'] != 'context_used' or not body['sources']:
            raise RuntimeError('The smoke question did not retrieve usable supporting context')
    report = {'origin':args.url, 'status':result.status_code, 'model':body['model'],
              'retrieval_status':body['retrieval_status'],
              'sources':[s['source'] for s in body['sources']]}
    path = Path('week5/evidence/rag-smoke.json')
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (httpx.HTTPError, RuntimeError) as exc:
        raise SystemExit(f'RAG smoke failed ({type(exc).__name__}); check server configuration and logs.') from None
