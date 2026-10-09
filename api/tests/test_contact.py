"""Offline validation tests. Run: pip install -r api/requirements.txt pytest; pytest api/tests"""
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("contact_api", Path(__file__).resolve().parents[1] / "function_app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BASE = {"kind": "contact", "firstName": "Jane", "lastName": "Smith", "email": "jane@example.org",
        "message": "Hello!", "turnstileToken": "token"}


def test_contact_valid():
    kind, fields, token = module.validate(BASE)
    assert kind == "contact"
    assert fields["message"] == "Hello!"
    assert token == "token"


@pytest.mark.parametrize("field,value", [
    ("email", "bad address"), ("firstName", ""), ("lastName", 100),
    ("message", "x" * 3001), ("turnstileToken", ""), ("kind", "other"),
])
def test_invalid_contact(field, value):
    with pytest.raises(ValueError):
        module.validate({**BASE, field: value})


def test_mailing_list_needs_consent():
    data = {**BASE, "kind": "mailing list", "phone": "847-555-0100"}
    with pytest.raises(ValueError):
        module.validate(data)
    data["consent"] = True
    assert module.validate(data)[0] == "mailing list"


def test_email_fixed_recipient_and_reply_to(monkeypatch):
    seen = {}
    class Sender:
        def begin_send(self, payload):
            seen.update(payload)
            return type("Poller", (), {"result": lambda self, timeout: {"status": "Succeeded"}})()
    monkeypatch.setattr(module, "settings", lambda key: "sender@example.azurecomm.net" if key == "ACS_SENDER_ADDRESS" else "fake-connection")
    monkeypatch.setattr(module.EmailClient, "from_connection_string", lambda s: Sender())
    module.send_email("contact", module.validate(BASE)[1])
    assert seen["recipients"]["to"] == [{"address": module.INBOX}]
    assert seen["replyTo"] == [{"address": BASE["email"]}]


def test_turnstile_rejects_wrong_hostname(monkeypatch):
    from io import BytesIO
    import json
    monkeypatch.setattr(module, "settings", lambda key: "secret" if key == "TURNSTILE_SECRET_KEY" else "www.marieparieboutique.com")
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda req, timeout: BytesIO(json.dumps({"success": True, "hostname": "evil.example"}).encode()))
    assert not module.verify_turnstile("token", "127.0.0.1")
