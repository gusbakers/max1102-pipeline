"""Measure real Gemini retrieval on labelled questions; never invent benchmark results."""
import asyncio
import json
from pathlib import Path
from google import genai
from google.genai import types
from api.rag import embed
from api.rag_config import Settings
from api.rag_store import search


async def evaluate():
    settings = Settings.load()
    records = [json.loads(line) for line in Path('knowledge/retrieval_cases.jsonl').read_text().splitlines()]
    results = []
    async with genai.Client(api_key=settings.api_key, vertexai=False,
        http_options=types.HttpOptions(timeout=20000,
            retry_options=types.HttpRetryOptions(attempts=1))).aio as client:
        for record in records:
            text = f"Estado del claim: {record['status']}. Pregunta: {record['question']}"
            vector = await embed(client, text, 'RETRIEVAL_QUERY')
            hits = search(settings, vector)
            sources = [hit['source'] for hit in hits]
            passed = record['expected_source'] in sources
            results.append({'case':record['id'], 'hit':passed, 'retrieved_sources':sources})
    report = {'cases':len(results), 'hit_at_k':sum(r['hit'] for r in results)/len(results),
              'k':settings.top_k, 'min_similarity':settings.min_similarity,
              'scope':'Small labelled project-document retrieval set; not a clinical or generation-quality benchmark.',
              'results':results}
    output = Path('week5/evidence/retrieval.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    try:
        asyncio.run(evaluate())
    except Exception as exc:
        raise SystemExit(f'Evaluation failed ({type(exc).__name__}); no score was produced.') from None
