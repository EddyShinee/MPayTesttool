import json
import base64
from datetime import datetime, timezone, timedelta
import streamlit as st


def _format_iso_datetime(value: str) -> str:
    """Render timestamp in GMT+7 with compact format."""
    if not value or value == "-":
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_gmt7 = dt.astimezone(timezone(timedelta(hours=7)))
        return dt_gmt7.strftime("%Y-%m-%d %H:%M:%S GMT+7")
    except Exception:
        return value


def _metric_card(label: str, value: str, value_size: str = "1rem") -> str:
    return f"""
    <div style="
        border: 1px solid rgba(250,250,250,0.14);
        border-radius: 10px;
        padding: 10px 20px;
        background: rgba(255,255,255,0.03);
        min-height: 92px;
        margin: 5px;
        ">
        <div style="font-size:0.80rem; opacity:0.82; margin-bottom:6px;">{label}</div>
        <div style="font-size:{value_size}; font-weight:600; line-height:1.25; word-break:break-word;">{value}</div>
    </div>
    """


def _decode_jwt_payload_unverified(jwt_token: str):
    try:
        payload_part = jwt_token.split(".")[1]
        padding = "=" * (-len(payload_part) % 4)
        decoded = base64.urlsafe_b64decode(payload_part + padding)
        return json.loads(decoded)
    except Exception:
        return None


def save_request_trace(prefix: str, trace) -> None:
    st.session_state[f"{prefix}_trace"] = trace
    # After a new request, prioritize showing the latest response trace.
    st.session_state[f"{prefix}_trace_view"] = "Response"


def set_error_state(prefix: str, error_text: str) -> None:
    st.session_state[f"{prefix}_res_payload"] = f"❌ Exception: {error_text}"
    st.session_state[f"{prefix}_trace"] = None
    st.session_state[f"{prefix}_trace_view"] = "Response"


def _legacy_trace(prefix: str):
    req_payload = st.session_state.get(f"{prefix}_req_payload", {})
    raw = st.session_state.get(f"{prefix}_res_payload", "")
    if not raw and not req_payload:
        return None
    status_code = 0
    duration_ms = 0
    body = raw
    try:
        header, body = raw.split("\n\n", 1)
        if "HTTP" in header:
            status_code = int(header.split("HTTP", 1)[-1].strip())
        if "⏱" in header and "s" in header:
            duration_ms = int(float(header.split("⏱", 1)[-1].split("s")[0].strip()) * 1000)
    except Exception:
        body = raw
    return {
        "request_payload_preview": json.dumps(req_payload, ensure_ascii=False) if isinstance(req_payload, dict) else str(req_payload),
        "response_body_raw": body,
        "http_status_code": status_code,
        "duration_ms": duration_ms,
        "request_started_at": "-",
        "request_ended_at": "-",
        "response_type": "text",
        "analysis": {"summary": f"HTTP {status_code}"},
        "error": None,
    }


def set_request_response_state(prefix: str, request_payload: dict, response_text: str, status_code: int, elapsed: float) -> None:
    """Backward-compatible helper for old pages."""
    st.session_state[f"{prefix}_req_payload"] = request_payload
    st.session_state[f"{prefix}_res_payload"] = f"⏱ {elapsed}s | HTTP {status_code}\n\n{response_text}"


def render_request_response(
    prefix: str,
    request_title: str = "### 📨 Request",
    response_title: str = "### 📬 Response",
    on_response_tab=None,
) -> None:
    trace = st.session_state.get(f"{prefix}_trace")
    if trace is None:
        trace = _legacy_trace(prefix)
    if trace is None:
        st.info("No request/response data yet.")
        return

    is_obj_trace = hasattr(trace, "http_status_code") and hasattr(trace, "request_payload_preview")

    st.markdown("### Request/Response Center")
    req_preview = trace.request_payload_preview if is_obj_trace else trace["request_payload_preview"]
    raw = trace.response_body_raw if is_obj_trace else trace["response_body_raw"]
    parsed = trace.response_body_parsed if is_obj_trace else None
    duration = trace.duration_ms if is_obj_trace else trace["duration_ms"]
    start = trace.request_started_at if is_obj_trace else trace["request_started_at"]
    end = trace.request_ended_at if is_obj_trace else trace["request_ended_at"]
    status_code = trace.http_status_code if is_obj_trace else trace["http_status_code"]
    analysis = trace.analysis if is_obj_trace else trace["analysis"]
    error_text = trace.error if is_obj_trace else trace["error"]

    # Unified summary panel (always visible, not split)
    # Row 1: Request Start takes 1/2 width.
    # Remaining 1/2 width is split into Method + HTTP Code.
    row1_left, row1_right = st.columns([1, 1])
    with row1_left:
        st.markdown(_metric_card("Request Start", _format_iso_datetime(start), value_size="0.92rem"), unsafe_allow_html=True)
    with row1_right:
        method_col, http_col = st.columns([1, 1])
        with method_col:
            st.markdown(_metric_card("Method", trace.method if is_obj_trace else "POST", value_size="1.05rem"), unsafe_allow_html=True)
        with http_col:
            st.markdown(_metric_card("HTTP Code", str(status_code), value_size="1.05rem"), unsafe_allow_html=True)

    # Row 2: Response End takes 1/2 width.
    # Duration takes the other 1/2 width (= Method + HTTP Code total width).
    row2_left, row2_right = st.columns([1, 1])
    with row2_left:
        st.markdown(_metric_card("Response End", _format_iso_datetime(end), value_size="0.92rem"), unsafe_allow_html=True)
    with row2_right:
        st.markdown(_metric_card("Duration", f"{duration} ms", value_size="1.05rem"), unsafe_allow_html=True)

    request_tab, response_tab = st.tabs(["Request", "Response"])

    with request_tab:
        st.markdown(request_title)
        st.write(
            {
                "url": trace.url if is_obj_trace else "-",
                "request_id": trace.request_id if is_obj_trace else "-",
                "request_headers": trace.request_headers_redacted if is_obj_trace else {},
            }
        )
        try:
            req_json = json.loads(req_preview)
            st.json(req_json)

            # If request contains JWT payload, show decrypted claims for easier debugging.
            if isinstance(req_json, dict) and isinstance(req_json.get("payload"), str):
                decoded_claims = _decode_jwt_payload_unverified(req_json["payload"])
                if decoded_claims is not None:
                    st.markdown("#### Decrypted Request Payload")
                    st.json(decoded_claims)
        except Exception:
            st.code(req_preview)

    with response_tab:
        st.markdown(response_title)
        st.info(f"Analysis: {analysis.get('summary', '')}")
        if parsed is not None:
            if isinstance(parsed, (dict, list)):
                st.json(parsed)
            else:
                st.code(str(parsed))
        else:
            try:
                st.json(json.loads(raw))
            except Exception:
                st.code(raw)
        if callable(on_response_tab):
            on_response_tab(parsed, raw)
