from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import time
import uuid
import xml.etree.ElementTree as ET
import requests


DEFAULT_TIMEOUT = (10, 30)


@dataclass
class RequestTrace:
    request_id: str
    api_name: str
    method: str
    url: str
    request_started_at: str
    request_ended_at: str
    duration_ms: int
    http_status_code: int
    ok: bool
    retry_count: int
    request_headers_redacted: dict
    request_payload_preview: str
    response_headers: dict = field(default_factory=dict)
    response_body_raw: str = ""
    response_body_parsed: dict | list | str | None = None
    response_type: str = "text"
    error_type: str | None = None
    error: str | None = None
    analysis: dict = field(default_factory=dict)

    # Backward-compatible aliases
    @property
    def status_code(self) -> int:
        return self.http_status_code

    @property
    def text(self) -> str:
        return self.response_body_raw

    @property
    def elapsed(self) -> float:
        return round(self.duration_ms / 1000, 2)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact_headers(headers: dict | None) -> dict:
    if not headers:
        return {}
    redacted = {}
    for key, value in headers.items():
        key_lower = str(key).lower()
        if key_lower in {"authorization", "x-api-key", "cookie"}:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def _preview_payload(payload) -> str:
    try:
        data = json.dumps(payload, ensure_ascii=False)
    except Exception:
        data = str(payload)
    return data[:2000]


def _parse_response_body(text: str):
    if not text:
        return None, "text"
    stripped = text.strip()
    try:
        return json.loads(stripped), "json"
    except Exception:
        pass
    if stripped.startswith("<"):
        try:
            root = ET.fromstring(stripped)
            return {"root_tag": root.tag}, "xml"
        except Exception:
            pass
    return stripped, "text"


def _build_analysis(trace: RequestTrace) -> dict:
    parsed = trace.response_body_parsed
    payload_fields = 0
    if trace.request_payload_preview.startswith("{"):
        try:
            payload_fields = len(json.loads(trace.request_payload_preview))
        except Exception:
            payload_fields = 0
    summary = f"HTTP {trace.http_status_code} in {trace.duration_ms}ms"
    if trace.error:
        summary = f"Failed: {trace.error}"
    return {
        "summary": summary,
        "response_type": trace.response_type,
        "payload_field_count": payload_fields,
        "has_error": bool(trace.error),
        "domain_hint": _domain_hint(parsed),
    }


def _domain_hint(parsed) -> str:
    if isinstance(parsed, dict):
        if "payload" in parsed:
            return "jwt_wrapped_response"
        if "respCode" in parsed or "respDesc" in parsed:
            return "payment_gateway_response"
    return "generic"


def post_json(
    url: str,
    payload: dict,
    api_name: str = "",
    headers: dict | None = None,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
    retries: int = 2,
) -> RequestTrace:
    """POST JSON with timeout and lightweight retry for transient failures."""
    if headers is None:
        headers = {"Content-Type": "application/json"}

    last_error = None
    last_error_type = None
    started_iso = _now_iso()
    start = time.time()
    response_headers = {}
    response_body = ""
    status_code = 0
    parsed = None
    response_type = "text"
    retry_count = 0
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            elapsed_ms = int((time.time() - start) * 1000)
            retry_count = attempt
            status_code = response.status_code
            response_headers = dict(response.headers)
            response_body = response.text
            parsed, response_type = _parse_response_body(response_body)
            # Retry only for server-side transient errors.
            if response.status_code >= 500 and attempt < retries:
                continue
            trace = RequestTrace(
                request_id=str(uuid.uuid4()),
                api_name=api_name or "api_call",
                method="POST",
                url=url,
                request_started_at=started_iso,
                request_ended_at=_now_iso(),
                duration_ms=elapsed_ms,
                http_status_code=response.status_code,
                ok=response.status_code == 200,
                retry_count=retry_count,
                request_headers_redacted=_redact_headers(headers),
                request_payload_preview=_preview_payload(payload),
                response_headers=response_headers,
                response_body_raw=response_body,
                response_body_parsed=parsed,
                response_type=response_type,
            )
            trace.analysis = _build_analysis(trace)
            return trace
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = str(exc)
            last_error_type = exc.__class__.__name__
            if attempt >= retries:
                break
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
            last_error_type = exc.__class__.__name__
            break

    elapsed_ms = int((time.time() - start) * 1000)
    trace = RequestTrace(
        request_id=str(uuid.uuid4()),
        api_name=api_name or "api_call",
        method="POST",
        url=url,
        request_started_at=started_iso,
        request_ended_at=_now_iso(),
        duration_ms=elapsed_ms,
        http_status_code=status_code,
        ok=False,
        retry_count=retry_count,
        request_headers_redacted=_redact_headers(headers),
        request_payload_preview=_preview_payload(payload),
        response_headers=response_headers,
        response_body_raw=response_body,
        response_body_parsed=parsed,
        response_type=response_type,
        error_type=last_error_type,
        error=last_error or "Request failed",
    )
    trace.analysis = _build_analysis(trace)
    return trace


def post_text(
    url: str,
    text_payload: str,
    api_name: str = "",
    headers: dict | None = None,
    timeout: tuple[int, int] = DEFAULT_TIMEOUT,
    retries: int = 1,
) -> RequestTrace:
    if headers is None:
        headers = {"content-type": "text/plain"}

    last_error = None
    last_error_type = None
    started_iso = _now_iso()
    start = time.time()
    response_headers = {}
    response_body = ""
    status_code = 0
    parsed = None
    response_type = "text"
    retry_count = 0
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, data=text_payload, headers=headers, timeout=timeout)
            elapsed_ms = int((time.time() - start) * 1000)
            retry_count = attempt
            status_code = response.status_code
            response_headers = dict(response.headers)
            response_body = response.text
            parsed, response_type = _parse_response_body(response_body)
            if response.status_code >= 500 and attempt < retries:
                continue
            trace = RequestTrace(
                request_id=str(uuid.uuid4()),
                api_name=api_name or "api_call",
                method="POST",
                url=url,
                request_started_at=started_iso,
                request_ended_at=_now_iso(),
                duration_ms=elapsed_ms,
                http_status_code=response.status_code,
                ok=response.status_code == 200,
                retry_count=retry_count,
                request_headers_redacted=_redact_headers(headers),
                request_payload_preview=_preview_payload(text_payload),
                response_headers=response_headers,
                response_body_raw=response_body,
                response_body_parsed=parsed,
                response_type=response_type,
            )
            trace.analysis = _build_analysis(trace)
            return trace
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = str(exc)
            last_error_type = exc.__class__.__name__
            if attempt >= retries:
                break
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
            last_error_type = exc.__class__.__name__
            break

    elapsed_ms = int((time.time() - start) * 1000)
    trace = RequestTrace(
        request_id=str(uuid.uuid4()),
        api_name=api_name or "api_call",
        method="POST",
        url=url,
        request_started_at=started_iso,
        request_ended_at=_now_iso(),
        duration_ms=elapsed_ms,
        http_status_code=status_code,
        ok=False,
        retry_count=retry_count,
        request_headers_redacted=_redact_headers(headers),
        request_payload_preview=_preview_payload(text_payload),
        response_headers=response_headers,
        response_body_raw=response_body,
        response_body_parsed=parsed,
        response_type=response_type,
        error_type=last_error_type,
        error=last_error or "Request failed",
    )
    trace.analysis = _build_analysis(trace)
    return trace

