import base64
import json
import jwt


def encode_hs256(payload: dict, secret_key: str) -> str:
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_jwt_payload_unverified(jwt_token: str) -> dict:
    """Decode payload part of JWT without signature verification."""
    try:
        payload_part = jwt_token.split(".")[1]
        padding = "=" * (-len(payload_part) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_part + padding)
        return json.loads(decoded_bytes)
    except Exception as exc:
        return {"error": str(exc)}

