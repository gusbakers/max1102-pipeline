"""Create local-only credentials once. Never print them or overwrite an existing file."""
import os
from pathlib import Path
import secrets
import shlex


def main():
    target = Path('week5/.env')
    if target.exists():
        print('week5/.env already exists; preserved.')
        return
    password = secrets.token_urlsafe(24)
    database = f'postgresql://max_week5:{password}@localhost:5433/max_week5'
    values = {'WEEK5_POSTGRES_PASSWORD': password,
        'RAG_DATABASE_URL': database, 'STREAM_DATABASE_URL': database,
        'APP_API_KEY': secrets.token_urlsafe(32), 'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
        'GEMINI_MODEL': os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite'), 'RAG_ENABLED': 'true',
        'RAG_COLLECTION': 'claims-project-v1', 'RAG_MIN_SIMILARITY': '0.55', 'RAG_TOP_K': '3',
        'KAFKA_BOOTSTRAP_SERVERS': 'localhost:9092', 'KAFKA_GROUP_ID': 'claims-pilot-v1'}
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write('\n'.join(f'{k}={shlex.quote(v)}' for k, v in values.items()) + '\n')
    print('Created week5/.env. Add your Gemini key there if needed; keep this file private.')


if __name__ == '__main__':
    main()
