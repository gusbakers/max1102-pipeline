import os
import secrets
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

try:
    from . import rag
    from .contracts import Claim
except ImportError:
    import rag
    from contracts import Claim

app = FastAPI(title="MAX Week 2 — Claim Summary con Gemini", version="2.0.0")
app.title = 'MAX Claims — Summary and RAG'
app.version = '5.0.0'
# Week4 observability
try:
    from .week4_observability import install as install_observability
except ImportError:
    from week4_observability import install as install_observability
install_observability(app)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Summary(BaseModel):
    claim_id: str
    summary: str
    model: str


def check_api_key(key: Annotated[str | None, Depends(api_key_header)]):
    expected = os.getenv("APP_API_KEY", "")
    if not expected:
        raise HTTPException(503, "Falta configurar APP_API_KEY en el servidor.")
    if not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(401, "API key incorrecta o ausente.")


@app.get("/health")
def health():
    # Comprueba el servidor; no llama al LLM ni comprueba su disponibilidad.
    return {"status": "ok"}


@app.post("/claims/llm-summary", response_model=rag.RagSummary | Summary,
          dependencies=[Depends(check_api_key)])
async def summarize(claim: Claim):
    if os.getenv('RAG_ENABLED', 'false').lower() == 'true':
        return await rag.summarize(claim)
    provider_key = os.getenv("GEMINI_API_KEY", "")
    if not provider_key:
        raise HTTPException(503, "Falta configurar GEMINI_API_KEY en el servidor.")
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    # Solo estos campos sintéticos van al proveedor. claim_id queda fuera del prompt.
    facts = (
        f"Monto: {claim.claim_amount:.2f}\n"
        f"Estado: {claim.claim_status}\n"
        f"Fecha del servicio: {claim.service_date.isoformat()}"
    )
    try:
        # La opción timeout del SDK de Google está expresada en milisegundos.
        async with genai.Client(
            api_key=provider_key,
            vertexai=False,
            http_options=types.HttpOptions(
                timeout=30000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ).aio as client:
            result = await client.models.generate_content(
                model=model,
                contents=facts,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "Resume un claim sintético en español, en una o dos frases. "
                        "Usa únicamente monto, estado y fecha recibidos. "
                        "Conserva exactamente sus valores. No supongas una moneda. "
                        "No inventes diagnósticos, razones del estado ni recomendaciones. "
                        "PAID significa pagado; DENIED, denegado; PENDING, pendiente. "
                        "Devuelve únicamente el resumen."
                    ),
                    temperature=0.2,
                    max_output_tokens=512,
                ),
            )
    except errors.APIError as exc:
        if exc.code == 429:
            raise HTTPException(429, "Cuota de Gemini agotada. Revisa tus límites gratuitos.") from None
        if exc.code in (401, 403):
            raise HTTPException(502, "Gemini rechazó la clave o el acceso del proyecto.") from None
        if exc.code == 404:
            raise HTTPException(502, "El modelo Gemini no está disponible. Revisa GEMINI_MODEL.") from None
        if exc.code == 504:
            raise HTTPException(504, "Gemini tardó demasiado en responder.") from None
        raise HTTPException(502, "No fue posible obtener el resumen de Gemini.") from None
    except httpx.TimeoutException:
        raise HTTPException(504, "Gemini tardó demasiado en responder.") from None
    except httpx.RequestError:
        raise HTTPException(502, "No fue posible conectar con Gemini.") from None
    if not result.candidates:
        raise HTTPException(502, "Gemini no devolvió un resumen utilizable.")
    candidate = result.candidates[0]
    text = (result.text or "").strip()
    if not text or candidate.finish_reason != types.FinishReason.STOP:
        raise HTTPException(502, "Gemini devolvió una respuesta vacía, bloqueada o incompleta.")
    return Summary(claim_id=claim.claim_id, summary=text, model=model)


class RagRequest(Claim):
    question: str = Field(default='Explica el estado del claim según la documentación del proyecto.',
                          min_length=3, max_length=500)


@app.post('/claims/rag-summary', response_model=rag.RagSummary,
          dependencies=[Depends(check_api_key)])
async def rag_summary(claim: RagRequest):
    return await rag.summarize(claim, claim.question)


@app.get('/rag/health', dependencies=[Depends(check_api_key)])
def rag_health():
    import psycopg
    settings = rag.load_settings()
    try:
        result = rag.rag_store.readiness(settings)
    except psycopg.Error:
        raise HTTPException(503, 'La base de conocimiento no está disponible.') from None
    if not result['ready']:
        raise HTTPException(503, 'La colección de conocimiento está vacía.')
    return result
