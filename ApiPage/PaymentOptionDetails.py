import streamlit as st
from utils.EnvSelector import select_environment
from ApiPage.common.http_client import post_json
from ApiPage.common.response_view import save_request_trace, set_error_state, render_request_response
from ApiPage.common.session_utils import init_clipboard_value, init_client_id
from ApiPage.common.ui import apply_submit_button_style


def render_payment_option_details():
    st.title("🧾 Payment Option Details")
    apply_submit_button_style()
    _, api_url = select_environment(key_suffix="payment_option_details", env_type="PaymentOptionDetails")

    col1, col2 = st.columns([1, 1])
    state_prefix = "payment_option_details"

    with col1:
        default_token = init_clipboard_value("payment_token_option", prefix="kSA", fallback="")
        payment_token = st.text_input("🔑 Payment Token", value=default_token, key="payment_token_option")

        default_client_id = init_client_id("client_id_option")
        client_id = st.text_input("🧾 Client ID", value=default_client_id, key="client_id_option")

        locale = st.text_input("🌍 Locale", "en")
        category_code = st.text_input("📂 Category Code", "GCARD")
        group_code = st.text_input("👥 Group Code", "CC")

        if st.button("🚀 Send Request", type="primary", use_container_width=True):
            if not payment_token:
                st.warning("⚠️ Payment Token is required.")
            else:
                payload = {
                    "paymentToken": payment_token,
                    "clientID": client_id,
                    "locale": locale,
                    "categoryCode": category_code,
                    "groupCode": group_code
                }
                try:
                    result = post_json(api_url, payload, api_name="PaymentOptionDetails")
                    if result.error:
                        set_error_state(state_prefix, result.error)
                        st.error(f"❌ {result.error}")
                    else:
                        save_request_trace(state_prefix, result)
                        if result.ok:
                            st.toast(f"✅ Request successful in {result.elapsed} seconds", icon="⏱")
                            st.success(f"✅ Request successful in ({result.elapsed} seconds)")
                        else:
                            st.toast(f"❌ Request failed in {result.elapsed}s", icon="⏱")
                            st.error(f"❌ Failed with HTTP {result.status_code}")
                except Exception as exc:
                    set_error_state(state_prefix, str(exc))
                    st.error("❌ Exception occurred")

    with col2:
        render_request_response(state_prefix)

if __name__ == "__main__":
    render_payment_option_details()
