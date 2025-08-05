import streamlit as st
import requests
import json
import datetime
import jwt  # PyJWT
import base64
import uuid
import pyperclip
import time
from utils.EnvSelector import select_environment

# Constants
KEY_PREFIX = str(uuid.uuid4())[:8]
DEFAULT_MERCHANT_ID = "704704000000000"
DEFAULT_SECRET_KEY = "0A85F7ED911FD69D3316ECDF20FCA4E138E590E7EF5D93009FEF1BEC5B2FF13F"
PAYMENT_CHANNEL_OPTIONS = ["ALL", "CC", "IPP", "APM", "QR", "VNPAY", "MOMO", "ZALOPAY"]


class PaymentTokenGenerator:
    def __init__(self):
        self.session_state = st.session_state

    @staticmethod
    def generate_invoice_no():
        return datetime.datetime.now().strftime("INV%y%m%d%H%M%S")

    @staticmethod
    def generate_idempotency_id():
        return f"idem-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    @staticmethod
    def decode_jwt_payload(jwt_token):
        try:
            payload_part = jwt_token.split('.')[1]
            padding = '=' * (-len(payload_part) % 4)
            decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
            return json.loads(decoded_bytes)
        except Exception as e:
            return {"error": str(e)}

    def initialize_session_state(self):
        """Initialize session state variables"""
        if "invoice_no" not in self.session_state:
            self.session_state["invoice_no"] = self.generate_invoice_no()
        if "idempotency_id" not in self.session_state:
            self.session_state["idempotency_id"] = self.generate_idempotency_id()

    def render_payment_channel_input(self):
        """Render payment channel selection with custom input option"""
        st.write("**Payment Channel:**")

        # Radio button for selection method
        channel_mode = st.radio(
            "Choose input method:",
            ["Select from list", "Custom input"],
            key=f"{KEY_PREFIX}_channel_mode",
            horizontal=True
        )

        if channel_mode == "Select from list":
            payment_channel = st.multiselect(
                "Select payment channels:",
                PAYMENT_CHANNEL_OPTIONS,
                default=["ALL"],
                key=f"{KEY_PREFIX}_payment_channel_select"
            )
        else:
            custom_input = st.text_input(
                "Enter custom payment channels (comma-separated):",
                placeholder="e.g., CUSTOM1,CUSTOM2,ALL",
                key=f"{KEY_PREFIX}_payment_channel_custom"
            )
            payment_channel = [ch.strip() for ch in custom_input.split(',') if ch.strip()]

        return payment_channel

    def render_basic_fields(self):
        """Render basic payment fields"""
        col1, col2 = st.columns(2)

        with col1:
            merchant_id = st.text_input(
                "Merchant ID",
                DEFAULT_MERCHANT_ID,
                key=f"{KEY_PREFIX}_merchant_id"
            )

            invoice_no = st.text_input(
                "Invoice No",
                value=self.session_state["invoice_no"],
                key=f"{KEY_PREFIX}_invoice_no"
            )

            idempotency_id = st.text_input(
                "Idempotency ID",
                value=self.session_state["idempotency_id"],
                key=f"{KEY_PREFIX}_idempotency_id"
            )

        with col2:
            description = st.text_input(
                "Description",
                f"Eddy - Payment {invoice_no}",
                key=f"{KEY_PREFIX}_description"
            )

            amount = st.number_input(
                "Amount",
                value=5000,
                min_value=1,
                key=f"{KEY_PREFIX}_amount"
            )

            currency_code = st.text_input(
                "Currency Code",
                "VND",
                key=f"{KEY_PREFIX}_currency_code"
            )

        # Payment channel section
        payment_channel = self.render_payment_channel_input()

        return {
            'merchant_id': merchant_id,
            'invoice_no': invoice_no,
            'idempotency_id': idempotency_id,
            'description': description,
            'amount': amount,
            'currency_code': currency_code,
            'payment_channel': payment_channel
        }

    def render_advanced_options(self):
        """Render advanced/optional fields"""
        optional_fields = {}

        with st.expander("➕ Advanced Options"):
            # URL Options
            st.subheader("🔗 URL Configuration")
            col1, col2 = st.columns(2)

            with col1:
                if st.checkbox("Frontend Return URL", key=f"{KEY_PREFIX}_checkbox_frontendReturnUrl"):
                    optional_fields['frontendReturnUrl'] = st.text_input(
                        "Frontend Return URL",
                        "https://eddy.io.vn/callback/webhook/payment",
                        key=f"{KEY_PREFIX}_frontend_return_url"
                    )

            with col2:
                if st.checkbox("Backend Return URL", key=f"{KEY_PREFIX}_checkbox_backendReturnUrl"):
                    optional_fields['backendReturnUrl'] = st.text_input(
                        "Backend Return URL",
                        "https://eddy.io.vn/callback/webhook/payment",
                        key=f"{KEY_PREFIX}_backend_return_url"
                    )

            # Payment Options
            st.subheader("💳 Payment Configuration")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.checkbox("Locale", key=f"{KEY_PREFIX}_checkbox_locale"):
                    optional_fields['locale'] = st.selectbox(
                        "Locale", ["vi", "en"],
                        key=f"{KEY_PREFIX}_locale"
                    )

                if st.checkbox("Request 3DS", key=f"{KEY_PREFIX}_checkbox_request3DS"):
                    optional_fields['request3DS'] = st.selectbox(
                        "Request 3DS", ["Y", "N"],
                        key=f"{KEY_PREFIX}_request3ds"
                    )

            with col2:
                if st.checkbox("Payment Expiry", key=f"{KEY_PREFIX}_checkbox_paymentExpiry"):
                    optional_fields['paymentExpiry'] = st.text_input(
                        "Payment Expiry (yyyy-MM-dd HH:mm:ss)",
                        key=f"{KEY_PREFIX}_payment_expiry"
                    )

                if st.checkbox("Agent Channel", key=f"{KEY_PREFIX}_checkbox_agentChannel"):
                    optional_fields['agentChannel'] = st.text_input(
                        "Agent Channel",
                        key=f"{KEY_PREFIX}_agent_channel"
                    )

            with col3:
                if st.checkbox("Immediate Payment", key=f"{KEY_PREFIX}_checkbox_immediatePayment"):
                    optional_fields['immediatePayment'] = st.selectbox(
                        "Immediate Payment", ["Y", "N"],
                        key=f"{KEY_PREFIX}_immediate_payment"
                    )

            # Token Options
            st.subheader("🎫 Token Configuration")
            col1, col2 = st.columns(2)

            with col1:
                if st.checkbox("Tokenize", key=f"{KEY_PREFIX}_checkbox_tokenize"):
                    optional_fields['tokenize'] = st.selectbox(
                        "Tokenize", [True, False],
                        key=f"{KEY_PREFIX}_tokenize"
                    )

                if st.checkbox("Customer Token Only", key=f"{KEY_PREFIX}_checkbox_customerTokenOnly"):
                    optional_fields['customerTokenOnly'] = st.checkbox(
                        "Customer Token Only",
                        key=f"{KEY_PREFIX}_customer_token_only"
                    )

            with col2:
                if st.checkbox("Customer Token", key=f"{KEY_PREFIX}_checkbox_customerToken"):
                    raw_token_input = st.text_area(
                        "Customer Token (comma-separated)",
                        key=f"{KEY_PREFIX}_customer_token"
                    )
                    optional_fields['customerToken'] = [
                        token.strip() for token in raw_token_input.split(',') if token.strip()
                    ]

                if st.checkbox("Tokenize Only", key=f"{KEY_PREFIX}_checkbox_tokenizeOnly"):
                    optional_fields['tokenizeOnly'] = st.checkbox(
                        "Tokenize Only",
                        key=f"{KEY_PREFIX}_tokenize_only"
                    )

            # Installment & Recurring fields (moved from nested expander)
            st.subheader("💰 Installment & Recurring")
            self._render_installment_fields(optional_fields)
            self._render_recurring_fields(optional_fields)

            # Other fields (moved from nested expander)
            st.subheader("🔧 Other Options")
            self._render_other_fields(optional_fields)

        return optional_fields

    def _render_installment_fields(self, optional_fields):
        """Render installment related fields"""
        col1, col2 = st.columns(2)

        with col1:
            if st.checkbox("Interest Type", key=f"{KEY_PREFIX}_checkbox_interestType"):
                optional_fields['interestType'] = st.selectbox(
                    "Interest Type", ["FULL", "PARTIAL"],
                    key=f"{KEY_PREFIX}_interest_type"
                )

            if st.checkbox("Installment Period Filter", key=f"{KEY_PREFIX}_checkbox_installmentPeriodFilter"):
                optional_fields['installmentPeriodFilter'] = st.text_input(
                    "Installment Period Filter",
                    key=f"{KEY_PREFIX}_installment_period_filter"
                )

        with col2:
            if st.checkbox("Installment Bank Filter", key=f"{KEY_PREFIX}_checkbox_installmentBankFilter"):
                optional_fields['installmentBankFilter'] = st.text_input(
                    "Installment Bank Filter",
                    key=f"{KEY_PREFIX}_installment_bank_filter"
                )

    def _render_recurring_fields(self, optional_fields):
        """Render recurring payment fields"""
        col1, col2 = st.columns(2)

        with col1:
            if st.checkbox("Recurring", key=f"{KEY_PREFIX}_checkbox_recurring"):
                optional_fields['recurring'] = st.selectbox(
                    "Recurring", ["Y", "N"],
                    key=f"{KEY_PREFIX}_recurring"
                )

            if st.checkbox("Recurring Amount", key=f"{KEY_PREFIX}_checkbox_recurringAmount"):
                optional_fields['recurringAmount'] = st.number_input(
                    "Recurring Amount", value=0,
                    key=f"{KEY_PREFIX}_recurring_amount"
                )

            if st.checkbox("Recurring Interval", key=f"{KEY_PREFIX}_checkbox_recurringInterval"):
                optional_fields['recurringInterval'] = st.text_input(
                    "Recurring Interval",
                    key=f"{KEY_PREFIX}_recurring_interval"
                )

        with col2:
            if st.checkbox("Recurring Count", key=f"{KEY_PREFIX}_checkbox_recurringCount"):
                optional_fields['recurringCount'] = st.number_input(
                    "Recurring Count", value=0,
                    key=f"{KEY_PREFIX}_recurring_count"
                )

            if st.checkbox("Charge Next Date", key=f"{KEY_PREFIX}_checkbox_chargeNextDate"):
                optional_fields['chargeNextDate'] = st.date_input(
                    "Charge Next Date",
                    key=f"{KEY_PREFIX}_charge_next_date"
                )

            if st.checkbox("Charge On Date", key=f"{KEY_PREFIX}_checkbox_chargeOnDate"):
                optional_fields['chargeOnDate'] = st.date_input(
                    "Charge On Date",
                    key=f"{KEY_PREFIX}_charge_on_date"
                )

    def _render_other_fields(self, optional_fields):
        """Render other miscellaneous fields"""
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.checkbox("Product Code", key=f"{KEY_PREFIX}_checkbox_productCode"):
                optional_fields['productCode'] = st.text_input(
                    "Product Code",
                    key=f"{KEY_PREFIX}_product_code"
                )

            if st.checkbox("Store Credentials", key=f"{KEY_PREFIX}_checkbox_storeCredentials"):
                optional_fields['storeCredentials'] = st.selectbox(
                    "Store Credentials", ["Y", "N"],
                    key=f"{KEY_PREFIX}_store_credentials"
                )

        with col2:
            if st.checkbox("Promotion Code", key=f"{KEY_PREFIX}_checkbox_promotionCode"):
                optional_fields['promotionCode'] = st.text_input(
                    "Promotion Code",
                    key=f"{KEY_PREFIX}_promotion_code"
                )

            if st.checkbox("Payment Route ID", key=f"{KEY_PREFIX}_checkbox_paymentRouteID"):
                optional_fields['paymentRouteID'] = st.text_input(
                    "Payment Route ID",
                    key=f"{KEY_PREFIX}_payment_route_id"
                )

        with col3:
            if st.checkbox("Allow Accumulate", key=f"{KEY_PREFIX}_checkbox_allowAccumulate"):
                optional_fields['allowAccumulate'] = st.selectbox(
                    "Allow Accumulate", ["Y", "N"],
                    key=f"{KEY_PREFIX}_allow_accumulate"
                )

            if st.checkbox("Max Accumulate Amount", key=f"{KEY_PREFIX}_checkbox_maxAccumulateAmount"):
                optional_fields['maxAccumulateAmount'] = st.number_input(
                    "Max Accumulate Amount", value=0,
                    key=f"{KEY_PREFIX}_max_accumulate_amount"
                )

    def send_payment_request(self, payload_data, secret_key, api_url, status_container=None, time_container=None):
        """Send payment token request with real-time updates"""
        try:
            # Start timing
            start_time = datetime.datetime.now()

            # Show initial status with progress
            if status_container:
                progress_bar = status_container.progress(0)
                status_text = status_container.empty()
                status_text.info("⏳ Initializing request...")

            if time_container:
                time_display = time_container.empty()
                time_display.markdown("⏰ **Start time:** " + start_time.strftime("%H:%M:%S"))

            # Step 1: Encoding JWT (20% progress)
            if status_container:
                progress_bar.progress(20)
                status_text.info("🔐 Encoding JWT token...")
            time.sleep(0.3)

            jwt_token = jwt.encode(payload_data, secret_key, algorithm="HS256")

            # Step 2: Preparing request (40% progress)
            if status_container:
                progress_bar.progress(40)
                status_text.info("📦 Preparing request payload...")
            time.sleep(0.2)

            # Step 3: Sending request (60% progress)
            if status_container:
                progress_bar.progress(60)
                status_text.info("🌐 Sending request to API...")

            # Update elapsed time during request
            request_start = time.time()

            response = requests.post(
                api_url,
                json={"payload": jwt_token},
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            # Step 4: Processing response (80% progress)
            if status_container:
                progress_bar.progress(80)
                status_text.info("📥 Processing API response...")
            time.sleep(0.2)

            # Step 5: Finalizing (100% progress)
            if status_container:
                progress_bar.progress(100)

            # Final update
            end_time = datetime.datetime.now()
            total_elapsed = (end_time - start_time).total_seconds()

            if status_container:
                if response.status_code == 200:
                    status_text.success(f"✅ Request completed successfully! 🎉")
                    # Keep progress bar at 100% briefly
                    time.sleep(0.5)
                    progress_bar.empty()
                else:
                    status_text.warning(f"⚠️ Request completed with status code: {response.status_code}")
                    progress_bar.empty()

            if time_container:
                time_display.markdown(f"""
                📊 **Request Timeline:**

                ⏰ **Start:** {start_time.strftime("%H:%M:%S")}  
                🏁 **End:** {end_time.strftime("%H:%M:%S")}  
                ⏱️ **Duration:** {total_elapsed:.2f}s

                {'🚀 **Status:** Success!' if response.status_code == 200 else '⚠️ **Status:** Check response'}
                """)

            return {
                'success': True,
                'jwt_token': jwt_token,
                'response': response.text,
                'status_code': response.status_code,
                'start_time': start_time,
                'end_time': end_time,
                'duration': total_elapsed
            }

        except Exception as e:
            end_time = datetime.datetime.now()
            total_elapsed = (end_time - start_time).total_seconds()

            if status_container:
                if 'progress_bar' in locals():
                    progress_bar.empty()
                if 'status_text' in locals():
                    status_text.error(f"❌ Request failed: {str(e)}")

            if time_container:
                if 'time_display' in locals():
                    time_display.markdown(f"""
                    📊 **Request Timeline:**

                    ⏰ **Started:** {start_time.strftime("%H:%M:%S")}  
                    💥 **Failed:** {end_time.strftime("%H:%M:%S")}  
                    ⏱️ **Duration:** {total_elapsed:.2f}s

                    ❌ **Status:** Failed - {str(e)}
                    """)

            return {
                'success': False,
                'error': str(e),
                'jwt_token': None,
                'response': None,
                'start_time': start_time,
                'end_time': end_time,
                'duration': total_elapsed
            }

    def render_response_section(self):
        """Render response display section"""
        # Show last request summary if available
        if "last_request_result" in st.session_state:
            last_result = st.session_state["last_request_result"]
            last_time = st.session_state.get("last_request_time", datetime.datetime.now())

            # Summary card
            if last_result['success']:
                st.success(f"""
                ✅ **Last Request: SUCCESS**  
                ⏱️ Duration: {last_result.get('duration', 0):.2f}s  
                📅 At: {last_time.strftime('%H:%M:%S')}
                """)
            else:
                st.error(f"""
                ❌ **Last Request: FAILED**  
                💥 Error: {last_result.get('error', 'Unknown')}  
                📅 At: {last_time.strftime('%H:%M:%S')}
                """)

            st.markdown("---")

        # Original response sections
        st.subheader("📤 Request Payload (Unencrypted):")
        payload_data = self.session_state.get("payload_data", {})
        st.json(payload_data)

        st.subheader("📤 Request Payload (JWT Encrypted):")
        request_payload = self.session_state.get("request_payload", "")
        if request_payload:
            st.code(request_payload, language="text")
            # Copy button below JWT
            if st.button("📋 Copy JWT", key=f"{KEY_PREFIX}_copy_jwt"):
                try:
                    pyperclip.copy(request_payload)
                    st.success("✅ JWT copied to clipboard!")
                except:
                    st.warning("⚠️ Cannot copy to clipboard. Manual copy needed")

        st.subheader("📥 API Response:")
        response_raw = self.session_state.get("response_payload", "")
        if response_raw:
            st.code(response_raw, language="json")

            # Try to decode JWT response
            try:
                decoded_response = json.loads(response_raw)
                if 'payload' in decoded_response:
                    st.subheader("🧩 Decoded JWT Response:")
                    decoded_payload = self.decode_jwt_payload(decoded_response['payload'])
                    st.json(decoded_payload)

                    # Action buttons - stacked vertically instead of columns
                    web_url = decoded_payload.get('webPaymentUrl')
                    if web_url:
                        st.markdown(f"[🌐 Open Payment URL]({web_url})")
                        st.markdown(f"[🌐 Open Webhook URL]({https://eddy.io.vn/callback/})")


                    if st.button("📋 Copy Payment Token", key=f"{KEY_PREFIX}_copy_token"):
                        payment_token = decoded_payload.get('paymentToken', 'Token not found')
                        try:
                            pyperclip.copy(payment_token)
                            st.success("✅ Payment token copied to clipboard!")
                        except:
                            st.warning("⚠️ Cannot copy to clipboard. Please copy manually:")
                            st.code(payment_token)
            except:
                st.info("💡 Unable to decode JWT response")


def render_payment_token():
    """Main function to render payment token page"""
    st.title("🔐 Payment Token Generator")

    # Initialize generator
    generator = PaymentTokenGenerator()
    generator.initialize_session_state()

    # Environment selection
    env, api_url = select_environment(key_suffix="payment_token", env_type="PaymentToken")

    # Layout
    col1_main, col2_main = st.columns([1, 1])

    with col1_main:
        st.subheader("⚙️ Configuration")

        # Basic fields
        basic_fields = generator.render_basic_fields()

        # Advanced options
        optional_fields = generator.render_advanced_options()

        # Secret key
        secret_key = st.text_input(
            "🔑 Merchant SHA Key",
            type="password",
            value=DEFAULT_SECRET_KEY,
            key=f"{KEY_PREFIX}_secret_key"
        )

        # Send request button
        if st.button("🚀 Generate Payment Token", key=f"{KEY_PREFIX}_send_request", type="primary"):
            # Update session state with new values
            st.session_state["invoice_no"] = generator.generate_invoice_no()
            st.session_state["idempotency_id"] = generator.generate_idempotency_id()

            # Prepare payload
            payload_data = {
                "merchantID": basic_fields['merchant_id'],
                "invoiceNo": st.session_state["invoice_no"],
                "description": f"Eddy - Payment {st.session_state['invoice_no']}",
                "amount": basic_fields['amount'],
                "currencyCode": basic_fields['currency_code'],
                "paymentChannel": basic_fields['payment_channel']
            }
            payload_data.update(optional_fields)

            # Create containers for real-time updates
            st.markdown("---")

            # Toast notification area with custom styling
            toast_container = st.empty()
            toast_container.info("🚀 **Starting payment token generation...** ⏳")

            # Status and timing containers with enhanced layout
            st.markdown("### 📊 Real-time Process Monitor")

            # Create tabs for better organization
            tab1, tab2 = st.tabs(["🔄 Process Status", "⏱️ Timing Info"])

            with tab1:
                status_container = st.empty()

            with tab2:
                time_container = st.empty()

            # Send request with real-time updates
            result = generator.send_payment_request(
                payload_data,
                secret_key,
                api_url,
                status_container=status_container,
                time_container=time_container
            )

            # Store results in session state
            st.session_state["payload_data"] = payload_data
            st.session_state["request_payload"] = result.get('jwt_token', '')
            st.session_state["response_payload"] = result.get('response', '')

            # Store request results in session state for persistent display
            st.session_state["last_request_result"] = result
            st.session_state["last_request_time"] = datetime.datetime.now()

            # Final toast notification with rich formatting
            if result['success']:
                toast_container.success(f"""
                🎉 **PAYMENT TOKEN GENERATED SUCCESSFULLY!** 🎉

                ⏱️ **Completed in:** {result.get('duration', 0):.2f} seconds  
                📅 **Finished at:** {result.get('end_time', datetime.datetime.now()).strftime('%H:%M:%S')}  
                🎯 **Status:** Ready to use!
                """)

                # Show celebration effect
                # st.balloons()

                # Add success metrics
                st.markdown("### 📊 Request Performance Metrics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric(
                        label="⚡ Response Time",
                        value=f"{result.get('duration', 0):.2f}s",
                        delta="Fast!" if result.get('duration', 0) < 2 else "Normal"
                    )
                with col2:
                    st.metric(
                        label="📊 Status Code",
                        value=result.get('status_code', 'N/A'),
                        delta="Success" if result.get('status_code') == 200 else "Check"
                    )
                with col3:
                    st.metric(
                        label="🔐 Token Status",
                        value="Generated",
                        delta="✅ Ready"
                    )

                # Add a button to continue/view results
                st.markdown("---")
                if st.button("📋 View Generated Results", key=f"{KEY_PREFIX}_view_results", type="secondary"):
                    st.rerun()

            else:
                toast_container.error(f"""
                💥 **PAYMENT TOKEN GENERATION FAILED!** 💥

                ❌ **Error:** {result.get('error', 'Unknown error')}  
                ⏱️ **Failed after:** {result.get('duration', 0):.2f} seconds  
                📅 **Failed at:** {result.get('end_time', datetime.datetime.now()).strftime('%H:%M:%S')}
                """)

                # Show error details in expandable section
                with st.expander("🔍 Detailed Error Information", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.error(f"**Error Message:**\n{result.get('error', 'Unknown error')}")
                    with col2:
                        if result.get('duration'):
                            st.info(f"**Time elapsed before failure:**\n{result.get('duration'):.2f} seconds")

                    # Error metrics
                    st.markdown("#### 📈 Error Metrics")
                    error_col1, error_col2 = st.columns(2)
                    with error_col1:
                        st.metric(
                            label="⏱️ Time to Failure",
                            value=f"{result.get('duration', 0):.2f}s"
                        )
                    with error_col2:
                        st.metric(
                            label="🔍 Error Type",
                            value="Request Failed"
                        )

                # Add retry button
                st.markdown("---")
                if st.button("🔄 Try Again", key=f"{KEY_PREFIX}_retry", type="secondary"):
                    st.rerun()

    with col2_main:
        st.subheader("📊 Results")
        generator.render_response_section()


if __name__ == "__main__":
    render_payment_token()