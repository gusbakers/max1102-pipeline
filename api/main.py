import os
import secrets
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="MAX Week 2 — Claim Summary con Gemini", version="2.0.0")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    claim_amount: Decimal = Field(ge=0, le=50000, max_digits=7, decimal_places=2)
    claim_status: Literal["PAID", "DENIED", "PENDING"]
    service_date: date


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


@app.post("/claims/llm-summary", response_model=Summary,
          dependencies=[Depends(check_api_key)])
async def summarize(claim: Claim):
    provider_key = os.getenv("GEMINI_API_KEY", "")
    if not provider_key:
        raise HTTPException(503, "Falta configurar GEMINI_API_KEY en el servidor.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
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
