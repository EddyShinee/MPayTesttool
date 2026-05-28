import streamlit as st
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import uuid
import time
import pyperclip
from utils.EnvSelector import select_environment
from ApiPage.common.config import get_secret
from ApiPage.common.http_client import post_json
from ApiPage.common.jwt_utils import decode_jwt_payload_unverified
from ApiPage.common.response_view import save_request_trace, render_request_response
from ApiPage.common.ui import apply_submit_button_style

KEY_PREFIX = "payment_pos"


def generate_invoice_no():
    """Generate a unique invoice number"""
    return datetime.datetime.now().strftime("INV-POS-%y%m%d%H%M%S")


def generate_idempotency_id():
    """Generate a unique idempotency ID"""
    return f"idem-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"


def initialize_session_state():
    """Initialize session state variables"""
    if "invoice_no" not in st.session_state:
        st.session_state["invoice_no"] = generate_invoice_no()
    if "idempotency_id" not in st.session_state:
        st.session_state["idempotency_id"] = generate_idempotency_id()


def render_input_form():
    """Render the input form section"""
    initialize_session_state()
    
    merchant_id = st.text_input("merchantID", "704704000000211", key=f"{KEY_PREFIX}_merchant_id_token")
    invoice_no = st.text_input("invoiceNo", value=st.session_state["invoice_no"], key=f"{KEY_PREFIX}_invoice_no_token")
    idempotency_id = st.text_input("idempotencyID", value=st.session_state["idempotency_id"], key=f"{KEY_PREFIX}_idempotency_id_token")
    description = st.text_input("description", f"Eddy - Payment {invoice_no}", key=f"{KEY_PREFIX}_description_token")
    amount = st.number_input("amount", value=5000, key=f"{KEY_PREFIX}_amount_token")
    currency_code = st.text_input("currencyCode", "VND", key=f"{KEY_PREFIX}_currency_code_token")
    payment_channel = [st.radio("paymentChannel", ["POSCC", "VNQR"], index=0, key=f"{KEY_PREFIX}_payment_channel_token")]
    user_defined_1 = st.text_input("userDefined1", "00024500937", key=f"{KEY_PREFIX}_user_defined_1_token")
    secret_key = st.text_input(
        "🔑 Merchant SHA Key",
        type="password",
        value=get_secret("MERCHANT_SHA_KEY_POS", get_secret("MERCHANT_SHA_KEY", "")),
        key=f"{KEY_PREFIX}_secret_key_token",
    )
    response_return_url = st.text_input(
        "responseReturnUrl",
        value="https://webhook.site/08fd12ec-4a71-4499-968c-0dbe729b8686",
        key=f"{KEY_PREFIX}_response_return_url_token"
    )
    customer_name = st.text_input("Customer Name", "Eddy", key=f"{KEY_PREFIX}_customer_name_token")
    customer_email = st.text_input("Customer Email", "eddy.vu@2c2p.com", key=f"{KEY_PREFIX}_customer_email_token")

    # Save state for UI
    form_data = {
        "merchant_id": merchant_id,
        "invoice_no": invoice_no,
        "idempotency_id": idempotency_id,
        "description": description,
        "amount": amount,
        "currency_code": currency_code,
        "payment_channel": payment_channel,
        "user_defined_1": user_defined_1,
        "secret_key": secret_key,
        "response_return_url": response_return_url,
        "customer_name": customer_name,
        "customer_email": customer_email
    }
    
    for key, value in form_data.items():
        st.session_state[key] = value
    
    return form_data


def handle_send_request_button():
    """Handle the send request button click"""
    if st.button("🔐 Send request Payment Token", key=f"{KEY_PREFIX}_send_request_button", type="primary", use_container_width=True):
        st.session_state["invoice_no"] = generate_invoice_no()
        st.session_state["idempotency_id"] = generate_idempotency_id()
        st.session_state["trigger_send_request"] = True
        st.session_state["request_completed"] = False  # Reset timer state
        st.rerun()


def create_payload_data(form_data):
    """Create the payload data for JWT encoding"""
    return {
        "merchantId": form_data["merchant_id"],
        "invoiceNo": form_data["invoice_no"],
        "description": f"Eddy - Payment {form_data['invoice_no']}",
        "amount": form_data["amount"],
        "currencyCode": form_data["currency_code"],
        "idempotencyID": form_data["idempotency_id"],
        "userDefined1": form_data["user_defined_1"]
    }


def create_api_payload(jwt_token, form_data):
    """Create the final API payload"""
    return {
        "paymentToken": jwt_token,
        "clientID": str(uuid.uuid4()).replace("-", ""),
        "locale": "en",
        "responseReturnUrl": form_data["response_return_url"],
        "payment": {
            "code": {
                "channelCode": form_data["payment_channel"][0]
            },
            "data": {
                "name": form_data["customer_name"],
                "email": form_data["customer_email"]
            }
        }
    }


def send_api_request(api_url, api_payload):
    """Send the API request and return response"""
    return post_json(api_url, api_payload, api_name="PaymentPOS", timeout=(10, 300), retries=2)


def process_request(form_data, api_url):
    """Process the payment request with real-time timer"""
    start_time = time.perf_counter()
    start_timestamp = datetime.datetime.now()
    start_timestamp_str = start_timestamp.strftime('%H:%M:%S.%f')[:-3]
    
    # Create placeholders for real-time updates
    timer_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Show initial status
    status_placeholder.info("🚀 **Sending request...**")
    st.toast("Starting request!", icon="🚀")
    
    # Real-time timer function
    def update_timer():
        current_time = time.perf_counter()
        elapsed = current_time - start_time
        timer_placeholder.info(f"⏱️ **Elapsed time: {elapsed:.1f}s**\n🕒 Started at: `{start_timestamp_str}`")
        return elapsed
    
    # Show initial timer
    elapsed_before_request = update_timer()
    
    # Create payloads with progress indication
    with st.spinner("Creating payload..."):
        payload_data = create_payload_data(form_data)
        st.session_state["payload_data"] = payload_data
        
        jwt_token = jwt.encode(payload_data, form_data["secret_key"], algorithm="HS256")
        st.session_state["request_payload"] = jwt_token
        
        api_payload = create_api_payload(jwt_token, form_data)
        st.session_state["api_payload"] = api_payload
    
    # Update timer after payload creation
    elapsed_before_request = update_timer()
    


    # Send request
    request_start_time = time.perf_counter()
    
    # Show timer during request
    elapsed = time.perf_counter() - start_time
    timer_placeholder.info(f"⏱️ **Elapsed time: {elapsed:.1f}s**\n🕒 Started at: `{start_timestamp_str}`\n🌐 **Sending API request...**")
    
    trace = send_api_request(api_url, api_payload)
    request_end_time = time.perf_counter()
    save_request_trace("payment_pos", trace)
    st.session_state["response_payload"] = trace.text
    
    # Calculate timing details
    total_time = time.perf_counter() - start_time
    request_duration = request_end_time - request_start_time
    end_timestamp = datetime.datetime.now()
    
    # Stop the timer
    st.session_state["request_completed"] = True
    
    # Store timing information
    timing_info = {
        "start_time": start_timestamp,
        "end_time": end_timestamp,
        "total_duration": total_time,
        "request_duration": request_duration,
        "elapsed_before_request": elapsed_before_request
    }
    st.session_state["timing_info"] = timing_info
    
    # Show final status
    if trace.error:
        status_placeholder.error("❌ **Request failed!**")
        st.error(trace.error)
    else:
        status_placeholder.success("✅ **Request successful!**")
    
    # Show detailed timing information
    with st.expander("⏱️ **Detailed Timing Information**", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🕒 Start Time", start_timestamp.strftime('%H:%M:%S.%f')[:-3])
            st.metric("⏳ Preparation", f"{elapsed_before_request:.3f}s")
            st.metric("⏱️ Total Time", f"{total_time:.3f}s")
        with col2:
            st.metric("🕐 End Time", end_timestamp.strftime('%H:%M:%S.%f')[:-3])
            st.metric("🌐 API Call", f"{request_duration:.3f}s")
            st.metric("📊 Performance", f"{(request_duration/total_time*100):.1f}%" if total_time > 0 else "0%")
    
    # Show final timer result
    timer_placeholder.success(f"✅ **Request completed in {total_time:.3f} seconds**")
    
    st.session_state["request_time"] = total_time


def render_payload_section():
    """Render the payload display section"""
    st.subheader("📤 Unencrypted Payload:")
    st.code(json.dumps(st.session_state.get("payload_data", {}), indent=2))

    st.subheader("📤 Encrypted Payload (JWT):")
    st.code(st.session_state.get("request_payload", ""))

    # st.subheader("🔎 Decoded JWT Payload:")
    # try:
    #     decoded_jwt = jwt.decode(
    #         st.session_state.get("request_payload", ""),
    #         st.session_state.get("secret_key", ""),
    #         algorithms=["HS256"]
    #     )
    #     st.json(decoded_jwt)
    # except Exception as e:
    #     st.warning(f"Unable to decode JWT with current secret key: {e}")

    st.subheader("📦 Final API Payload:")
    st.code(json.dumps(st.session_state.get("api_payload", {}), indent=2))


def render_response_section():
    """Render the response display section"""
    render_request_response("payment_pos", request_title="### 📨 Request Trace", response_title="### 📬 Response Trace")
    st.subheader("📥 Response from API:")
    response_raw = st.session_state.get("response_payload", "")
    
    with st.expander("📩 Raw API Response", expanded=True):
        st.code(response_raw, language='json')

    if response_raw:
        try:
            decoded_response = json.loads(response_raw)
            if 'payload' in decoded_response:
                st.subheader("🧩 Decoded JWT Response:")
                st.json(decode_jwt_payload_unverified(decoded_response['payload']))
                
                # Web payment URL and copy invoice ID
                row1_col1, row1_col2 = st.columns(2)
                with row1_col1:
                    web_url = decode_jwt_payload_unverified(decoded_response['payload']).get('webPaymentUrl')
                    if web_url:
                        st.markdown(f"[🌐 Open Web Payment URL]({web_url})", unsafe_allow_html=True)
                with row1_col2:
                    if st.button("📋 Copy Invoice ID", key=f"{KEY_PREFIX}_copy_invoice_id_button"):
                        invoice_id = st.session_state.get("invoice_no", "invoice_no not found")
                        try:
                            pyperclip.copy(invoice_id)
                            st.toast("✅ Invoice ID copied to clipboard!", icon="📋")
                        except Exception:
                            st.warning("⚠️ Unable to copy Invoice ID to clipboard. Please copy it manually.")
                            st.code(invoice_id)
        except Exception:
            st.info("Unable to decode JWT response or 'payload' not found in response.")


def render_payment_pos():
    """Main function to render the Payment POS page"""
    st.title("🔐 Payment POS")
    apply_submit_button_style()
    env, api_url = select_environment(key_suffix="payment_pos", env_type="PaymentPOS")

    col1, col2 = st.columns(2)
    
    with col1:
        # Render input form
        form_data = render_input_form()
        
        # Handle send request button
        handle_send_request_button()

        # Process request if triggered
        if st.session_state.get("trigger_send_request", False):
            st.session_state["trigger_send_request"] = False
            process_request(form_data, api_url)

    # Right column: Show request/response/debug
    with col2:
        render_payload_section()
        render_response_section()


if __name__ == "__main__":
    render_payment_pos()
