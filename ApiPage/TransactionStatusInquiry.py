import streamlit as st
from utils.EnvSelector import select_environment
from ApiPage.common.http_client import post_json
from ApiPage.common.response_view import save_request_trace, set_error_state, render_request_response
from ApiPage.common.session_utils import init_clipboard_value, init_client_id
from ApiPage.common.ui import apply_submit_button_style


def render_transaction_status_inquiry():
    st.title("🔍 Transaction Status Inquiry")
    apply_submit_button_style()
    _, api_url = select_environment(key_suffix="transaction_status_inquiry", env_type="TransactionStatusInquiry")

    col1, col2 = st.columns([1, 1])
    state_prefix = "txn_status_inquiry"

    with col1:
        default_token = init_clipboard_value("txn_status_payment_token", prefix="kSA", fallback="")
        payment_token = st.text_input("🔑 Payment Token", value=default_token, key="txn_status_payment_token")
        default_client_id = init_client_id("txn_status_client_id")
        client_id = st.text_input("🧾 Client ID", value=default_client_id, key="txn_status_client_id")

        locale = st.text_input("🌍 Locale", "en")
        # category_code and group_code are no longer used in the payload
        # category_code = st.text_input("📂 Category Code", "GCARD")
        # group_code = st.text_input("👥 Group Code", "CC")

        additional_info = st.radio("Include Additional Info?", options=["Yes", "No"], index=0)
        additional_info_bool = additional_info == "Yes"

        if st.button("🚀 Send Request", type="primary", use_container_width=True):
            if not payment_token:
                st.warning("⚠️ Payment Token is required.")
            else:
                payload = {
                    "paymentToken": payment_token,
                    "clientID": client_id,
                    "locale": locale,
                    "additionalInfo": additional_info_bool
                }
                try:
                    result = post_json(api_url, payload, api_name="TransactionStatusInquiry")
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
        render_request_response(
            state_prefix,
            request_title="### 📤 Transaction Inquiry Request",
            response_title="### 📥 Transaction Inquiry Response",
        )

if __name__ == "__main__":
    render_transaction_status_inquiry()
