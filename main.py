import streamlit as st
st.set_page_config(page_title="2C2P API Simulator", layout="wide")

import Sidebar.Sidebar as Sidebar
from ApiPage import PaymentToken, PaymentAction, DoPayment, PaymentOptions, PaymentOptionDetails, TransactionStatusInquiry, PaymentInquiry, PaymentPOS, WebhookReceiver, Analysist

HARDCODED_USERNAME = "eddy.vu"
HARDCODED_PASSWORD = "Abcde@12345"


def render_login():
    st.title("🔐 Login")
    st.caption("Please sign in to access API tools.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Account")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

    if submitted:
        if username == HARDCODED_USERNAME and password == HARDCODED_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.success("Login successful.")
            st.rerun()
        else:
            st.error("Invalid account or password.")


if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    render_login()
    st.stop()

st.sidebar.title("Payment API List")
st.sidebar.success(f"Logged in as: {st.session_state.get('username', HARDCODED_USERNAME)}")
if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state.pop("username", None)
    st.rerun()

api_selected = st.sidebar.radio("Choose API", Sidebar.api_list)

api_pages = {
    "Payment Token": PaymentToken.render_payment_token,
    "Payment Action": PaymentAction.render_payment_action,
    "Do Payment": DoPayment.render_do_payment,
    "Payment Options": PaymentOptions.render_payment_options,
    "Payment Option Details": PaymentOptionDetails.render_payment_option_details,
    "Transaction Status Inquiry": TransactionStatusInquiry.render_transaction_status_inquiry,
    "Payment Inquiry": PaymentInquiry.render_payment_inquiry,
    "Payment POS": PaymentPOS.render_payment_pos,
    "Webhook Receiver": WebhookReceiver.render_webhook_receiver,
    "Analysist": Analysist.render_analysist
    # thêm các API khác tại đây nếu đã định nghĩa
}

if api_selected in api_pages:
    api_pages[api_selected]()
else:
    st.warning(f"🚧 Trang '{api_selected}' chưa được tạo.")
