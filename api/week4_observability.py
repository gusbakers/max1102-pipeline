"""Request metadata only: no API keys, request bodies, or claim IDs."""
import json
import logging
import time
import uuid
from pathlib import Path

log = logging.getLogger('uvicorn.error')

def install(app):
    @app.get('/version')
    def version():
        p = Path(__file__).with_name('build-info.json')
        return json.loads(p.read_text()) if p.exists() else {'commit': 'development'}

    @app.middleware('http')
    async def request_metadata(request, call_next):
        started = time.perf_counter()
        status = 500
        request_id = uuid.uuid4().hex
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers['X-Request-ID'] = request_id
            return response
        finally:
            route = request.scope.get('route')
            log.info(json.dumps({
                'event': 'http_request', 'request_id': request_id,
                'method': request.method,
                'route': getattr(route, 'path', 'unmatched'),
                'status': status,
                'duration_ms': round((time.perf_counter() - started) * 1000, 2),
            }))
