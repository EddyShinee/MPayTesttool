"""Lightweight smoke tests for request/response center."""

try:
    from ApiPage.common.http_client import _redact_headers, _parse_response_body
except ModuleNotFoundError:
    from http_client import _redact_headers, _parse_response_body


def run_smoke_tests():
    redacted = _redact_headers({"Authorization": "Bearer abc", "Content-Type": "application/json"})
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["Content-Type"] == "application/json"

    parsed_json, parsed_type = _parse_response_body('{"ok": true, "code": 200}')
    assert parsed_type == "json"
    assert isinstance(parsed_json, dict) and parsed_json.get("ok") is True

    parsed_xml, xml_type = _parse_response_body("<root><ok/></root>")
    assert xml_type == "xml"
    assert isinstance(parsed_xml, dict) and parsed_xml.get("root_tag") == "root"

    parsed_text, text_type = _parse_response_body("plain-response")
    assert text_type == "text"
    assert parsed_text == "plain-response"


if __name__ == "__main__":
    run_smoke_tests()
    print("Smoke tests passed.")

