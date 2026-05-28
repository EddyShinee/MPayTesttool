import json
import streamlit as st
import jwt
from utils.EnvSelector import select_environment
from ApiPage.common.config import get_secret
from ApiPage.common.http_client import post_json
from ApiPage.common.jwt_utils import encode_hs256
from ApiPage.common.response_view import save_request_trace, set_error_state, render_request_response
from ApiPage.common.session_utils import init_clipboard_value
from ApiPage.common.ui import apply_submit_button_style


KEY_PREFIX = "payment_inquiry"


def render_payment_inquiry():

    st.title("🧾 Payment Inquiry")
    apply_submit_button_style()
    _, api_url = select_environment(key_suffix="payment_inquiry", env_type="PaymentInquiry")

    col1, col2 = st.columns([1, 1])

    with col1:
        merchant_id = st.text_input("🏢 Merchant ID", "704704000000000")
        # --- Invoice No session state initialization from clipboard ---
        if "invoice_no" not in st.session_state:
            init_clipboard_value("invoice_no", prefix="INV", fallback="254b77aabc")
        invoice_no = st.text_input("🧾 Invoice No", value=st.session_state.invoice_no, key="invoice_no")
        locale = st.text_input("🌍 Locale", "en")
        default_secret = get_secret("MERCHANT_SHA_KEY", "")
        if f"{KEY_PREFIX}_secret_key_token" not in st.session_state:
            st.session_state[f"{KEY_PREFIX}_secret_key_token"] = default_secret
        
        secret_key = st.text_input("🔑 Merchant SHA Key", type="password", value=st.session_state[f"{KEY_PREFIX}_secret_key_token"], key=f"{KEY_PREFIX}_secret_key_token")

        if st.button("🚀 Send Request", type="primary", use_container_width=True):
            payload = {
                "merchantID": merchant_id,
                "invoiceNo": invoice_no,
                "locale": locale
            }
            try:
                st.session_state["payment_inquiry_req_payload"] = payload
                if not secret_key:
                    st.warning("⚠️ Merchant SHA Key is required.")
                    return
                encoded_payload = encode_hs256(payload, secret_key)
                final_payload = {"payload": encoded_payload}
                st.session_state["payment_inquiry_final_payload"] = final_payload
                result = post_json(api_url, final_payload, api_name="PaymentInquiry")
                if result.error:
                    set_error_state("payment_inquiry", result.error)
                    st.error(f"❌ {result.error}")
                else:
                    save_request_trace("payment_inquiry", result)
                    if result.ok:
                        st.toast(f"✅ Request successful in {result.elapsed} seconds", icon="⏱")
                        st.success(f"✅ Request successful in ({result.elapsed} seconds)")
                    else:
                        st.toast(f"❌ Request failed in {result.elapsed}s", icon="⏱")
                        st.error(f"❌ Failed with HTTP {result.status_code}")
            except Exception as exc:
                set_error_state("payment_inquiry", str(exc))
                st.error("❌ Exception occurred")

    with col2:
        st.markdown("### 🧾 Raw Payload (Before Encryption)")
        st.json(st.session_state.get("payment_inquiry_req_payload", {}))

        st.markdown("### 📨 Request")
        st.json(st.session_state.get("payment_inquiry_final_payload", {}))

        # st.markdown("### 🔓 Decrypted Payload (JWT Claims)")
        # try:
        #     import jwt
        #     decoded = jwt.decode(
        #         st.session_state.get('final_payload', {}).get("payload", ""),
        #         secret_key,
        #         algorithms=["HS256"]
        #     )
        #     st.json(decoded)
        # except Exception as e:
        #     st.warning(f"Could not decode JWT: {e}")

        render_request_response("payment_inquiry", request_title="### 📨 Request Trace", response_title="### 📬 Response Trace")

        st.markdown("### 📬 Response (legacy decode)")
        parsed_response = {}
        try:
            trace = st.session_state.get("payment_inquiry_trace")
            raw_response = trace.response_body_raw if trace else st.session_state.get("payment_inquiry_res_payload", "")
            parsed_response = json.loads(raw_response)
            st.json(parsed_response)
        except (json.JSONDecodeError, TypeError):
            st.code("No response")

        st.markdown("### 🔓 Decrypted Response Payload (JWT Claims)")
        try:
            jwt_payload = parsed_response.get("payload")
            if jwt_payload:
                decoded_res = jwt.decode(jwt_payload, secret_key, algorithms=["HS256"])
                st.json(decoded_res)
            else:
                st.info("No payload to decode in response.")
        except Exception as e:
            st.warning(f"Could not decode response JWT: {e}")

if __name__ == "__main__":
    render_payment_inquiry()
