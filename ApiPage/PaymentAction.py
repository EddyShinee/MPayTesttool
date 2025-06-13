import streamlit as st
import os
import json
import requests
from datetime import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from jwcrypto import jwk, jws, jwe
import xml.etree.ElementTree as ET
from cryptography.hazmat.primitives.serialization import pkcs12
import xml.dom.minidom
from utils.EnvSelector import select_environment

st.title("🔐 Payment Action")
# --- Chọn môi trường ---

env, api_url = select_environment(key_suffix="payment_action", env_type="PaymentAction")

# Pretty print XML helper
def pretty_print_xml(xml_str: str) -> str:
    parsed = xml.dom.minidom.parseString(xml_str)
    return parsed.toprettyxml(indent="  ")

private_key_file = st.file_uploader("🔐 Upload Private Key (.pfx, .p12, .pem, .key)", type=["pfx", "p12", "pem", "key"])
# Load previously saved password if available
config_path = "config.json"
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        saved_config = json.load(f)
    if "last_password" in saved_config:
        private_key_password = st.text_input("🔑 Private Key Password", type="password", value=saved_config["last_password"])
else:
    private_key_password = st.text_input("🔑 Private Key Password", type="password")

public_cert_file = st.file_uploader("📄 Upload Public Certificate (.cer)", type=["cer", "crt"])

# Validate uploaded file types
if private_key_file is not None and not private_key_file.name.lower().endswith(('.pfx', '.p12', '.pem', '.key')):
    st.error("❌ Invalid Private Key file. Please upload a .pfx, .p12, .pem, or .key file.")
if public_cert_file is not None and not public_cert_file.name.lower().endswith(('.cer', '.crt')):
    st.error("❌ Invalid Public Certificate file. Please upload a .cer or .crt file.")

if private_key_file is not None and public_cert_file is not None:
    try:
        if private_key_file.name.lower().endswith((".pfx", ".p12")):
            pfx_data = private_key_file.read()
            private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                pfx_data, password=private_key_password.encode(), backend=default_backend()
            )
        elif private_key_file.name.lower().endswith((".pem", ".key")):
            pem_data = private_key_file.read()
            private_key = serialization.load_pem_private_key(
                pem_data,
                password=private_key_password.encode() if private_key_password else None,
                backend=default_backend()
            )
            certificate = None
        else:
            raise ValueError("Unsupported private key file type.")
        # Save current config
        config_to_save = {
            "last_password": private_key_password,
            "last_private_key_filename": private_key_file.name,
            "last_cert_filename": public_cert_file.name
        }
        with open(config_path, "w") as f:
            json.dump(config_to_save, f)
        # Convert private key to PEM format for jwcrypto JWK import
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        private_jwk = jwk.JWK.from_pem(private_key_pem)
        public_cert_data = public_cert_file.read()
        try:
            public_jwk = jwk.JWK.from_pem(public_cert_data)
        except Exception:
            from cryptography import x509
            cert = x509.load_der_x509_certificate(public_cert_data, default_backend())
            pem_cert = cert.public_bytes(serialization.Encoding.PEM)
            public_jwk = jwk.JWK.from_pem(pem_cert)
    except Exception as e:
        st.error(f"❌ Error loading or converting key files: {e}")
        st.stop()

col1, col2 = st.columns(2)

with col1:
    version = st.text_input("Version", value="3.8")
    mid = st.text_input("Merchant ID", value="704704000000211")
    invoice_no = st.text_input("Invoice No", value="01a00a81-364c-48f4-8278-3aef4ec61399")
    amount = st.text_input("Action Amount", value="12000")
    processType = st.selectbox("Process Type", ["I", "R", "V"])
    timestamp = st.text_input("Timestamp", value=datetime.now().strftime('%y%m%d%H%M%S'))
    recurring_id = st.text_input("Recurring Unique ID", value="")

    if processType in ["R", "V"]:
        notifyURL = st.text_input("Notify URL", value="https://webhook.site/da1c7de2-65c7-44c4-a05d-63e13910f3a0")
    else:
        notifyURL = ""

send_request = st.button("🔁 Send Request to 2C2P")

if send_request:
    import time
    with st.spinner("⏳ Đang gửi request đến 2C2P..."):
        start_time = time.time()
    # Check if JWKs are loaded
    if 'public_jwk' not in locals() or 'private_jwk' not in locals():
        st.error("❌ Public or Private JWK is not loaded properly. Please check your uploaded key files.")
        st.stop()
    root = ET.Element("PaymentProcessRequest")
    ET.SubElement(root, "version").text = version
    ET.SubElement(root, "timeStamp").text = timestamp
    ET.SubElement(root, "merchantID").text = mid
    ET.SubElement(root, "invoiceNo").text = invoice_no
    ET.SubElement(root, "actionAmount").text = amount
    ET.SubElement(root, "recurringUniqueID").text = recurring_id
    ET.SubElement(root, "processType").text = processType
    ET.SubElement(root, "notifyURL").text = notifyURL
    xml_payload = ET.tostring(root, encoding="unicode")

    with col2:
        st.markdown("### 📄 XML Payload (cleaned):")
        st.code(xml_payload, language="xml")

        jwe_token_obj = jwe.JWE(xml_payload.encode('utf-8'),
                                protected={"alg": "RSA-OAEP", "enc": "A256GCM", "kid": "1"})
        jwe_token_obj.add_recipient(public_jwk)
        jwe_token = jwe_token_obj.serialize(compact=True)

        st.markdown("### 🔐 JWE (Encrypted XML):")
        st.code(jwe_token, language="text")

        jws_token_obj = jws.JWS(jwe_token.encode('utf-8'))
        jws_token_obj.add_signature(private_jwk, protected={"alg": "PS256", "kid": "1"})
        final_token = jws_token_obj.serialize(compact=True)

        st.markdown("### 🖋️ Final JWS over JWE:")
        st.code(final_token)

    headers = {'content-type': 'text/plain'}
    response = requests.post(api_url, data=final_token, headers=headers, timeout=60)

    end_time = time.time()
    duration = round(end_time - start_time, 2)

    st.markdown("### 📤 Sent JWS Token:")
    st.code(final_token)

    if response.status_code == 200:
        st.success(f"✅ Gửi yêu cầu thành công! ⏱ Xử lý {duration} giây.")
    else:
        st.warning(f"⚠️ Gửi yêu cầu thất bại. Mã trạng thái: {response.status_code} ⏱ Xử lý {duration} giây.")
    st.markdown("### 📦 Raw Encrypted Response:")
    st.code(response.text)

    def is_jwe_compact_format(text):
        return len(text.split(".")) == 5

    def is_jws_compact_format(text):
        return len(text.split(".")) == 3

    xml_result = None
    try:
        if is_jws_compact_format(response.text):
            incoming_jws = jws.JWS()
            incoming_jws.deserialize(response.text.strip())
            incoming_jws.verify(public_jwk)
            jwe_payload = incoming_jws.payload.decode("utf-8")

            incoming_jwe = jwe.JWE()
            incoming_jwe.deserialize(jwe_payload.strip())
            incoming_jwe.decrypt(private_jwk)
            xml_result = incoming_jwe.payload.decode("utf-8")

        elif is_jwe_compact_format(response.text):
            incoming_jwe = jwe.JWE()
            incoming_jwe.deserialize(response.text.strip())
            incoming_jwe.decrypt(private_jwk)
            xml_result = incoming_jwe.payload.decode("utf-8")

        else:
            raise ValueError("Response is not in compact JWS or JWE format.")

    except Exception as e:
        import traceback
        st.error(f"❌ Error decoding both JWS and JWE:\n{traceback.format_exc()}")
        st.markdown("### ❌ Raw Response:")
        st.code(response.text)

    if xml_result:
        st.markdown("### ✅ Final Decrypted 2C2P Response:")
        try:
            formatted_xml = ET.tostring(ET.fromstring(xml_result), encoding='unicode', method='xml')
            pretty = pretty_print_xml(formatted_xml)
            st.code(pretty, language="xml")
        except Exception:
            pretty = pretty_print_xml(xml_result)
            st.code(pretty, language="xml")