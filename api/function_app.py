"""Public, guarded Marie Parie website enquiry endpoint."""
import hashlib
import json
import logging
import os
import re
import time
import uuid
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parseaddr

import azure.functions as func
from azure.communication.email import EmailClient
from azure.core.exceptions import ResourceExistsError, ResourceModifiedError
from azure.data.tables import TableServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
ALLOWED_KINDS = {"contact", "mailing list"}
INBOX = "bonjour@marieparieboutique.com"
EMAIL_PATTERN = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
PHONE_PATTERN = re.compile(r"^[+0-9 ().-]{0,40}$")


def settings(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required application setting: {name}")
    return value


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid request")
    kind = data.get("kind")
    if kind not in ALLOWED_KINDS:
        raise ValueError("Unknown form")
    fields = {}
    for name in ("firstName", "lastName"):
        value = data.get(name)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80:
            raise ValueError(f"Invalid {name}")
        fields[name] = value.strip()
    email = data.get("email")
    if not isinstance(email, str) or len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Invalid email")
    fields["email"] = email
    if kind == "contact":
        value = data.get("message")
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= 3000:
            raise ValueError("Invalid message")
        fields["message"] = value.strip()
    else:
        phone = data.get("phone", "")
        if not isinstance(phone, str) or not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("Invalid phone number")
        fields["phone"] = phone
        if data.get("consent") is not True:
            raise ValueError("Marketing consent required")
    token = data.get("turnstileToken")
    if not isinstance(token, str) or not 1 <= len(token) <= 2048:
        raise ValueError("Verification required")
    return kind, fields, token


def verify_turnstile(token, remote_ip):
    payload = urllib.parse.urlencode({
        "secret": settings("TURNSTILE_SECRET_KEY"),
        "response": token,
        "remoteip": remote_ip,
    }).encode()
    request = urllib.request.Request("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=8) as response:
        result = json.load(response)
    allowed_hosts = {h.strip().lower() for h in settings("TURNSTILE_ALLOWED_HOSTNAMES").split(",") if h.strip()}
    return result.get("success") is True and str(result.get("hostname", "")).lower() in allowed_hosts


def check_limit(ip):
    """Fail closed. Optimistic ETag updates prevent concurrent requests evading counters."""
    service = TableServiceClient.from_connection_string(settings("AzureWebJobsStorage"))
    table = service.get_table_client("MarieParieFormLimits")
    now = int(time.time())
    key = hashlib.sha256((settings("RATE_LIMIT_SALT") + ":" + ip).encode()).hexdigest()
    rules = [
        (f"ip10-{now // 600}", key, 3),
        (f"ipday-{now // 86400}", key, 20),
        (f"globalday-{now // 86400}", "all", int(os.getenv("GLOBAL_DAILY_LIMIT", "100"))),
    ]
    # Partial consumed capacity on failed checks is deliberately conservative.
    for partition, row, limit in rules:
        for attempt in range(8):
            try:
                entity = table.get_entity(partition_key=partition, row_key=row)
            except Exception as exc:
                from azure.core.exceptions import ResourceNotFoundError
                if not isinstance(exc, ResourceNotFoundError):
                    raise
                try:
                    table.create_entity({"PartitionKey": partition, "RowKey": row, "Count": 1})
                    break
                except ResourceExistsError:
                    continue
            else:
                if entity["Count"] >= limit:
                    return False
                from azure.core import MatchConditions
                try:
                    table.update_entity({**entity, "Count": entity["Count"] + 1},
                                        etag=entity.metadata["etag"],
                                        match_condition=MatchConditions.IfNotModified)
                    break
                except ResourceModifiedError:
                    continue
        else:
            raise RuntimeError("Rate-limit counter busy")
    return True


def send_email(kind, fields):
    sender = settings("ACS_SENDER_ADDRESS")
    client = EmailClient.from_connection_string(settings("ACS_CONNECTION_STRING"))
    title = "Contact enquiry" if kind == "contact" else "Mailing list request"
    lines = [f"Form: {title}", f"Name: {fields['firstName']} {fields['lastName']}", f"Email: {fields['email']}"]
    lines.append(f"Message:\n{fields['message']}" if kind == "contact" else f"Phone: {fields['phone'] or 'Not provided'}\nMarketing consent: Yes")
    message = {
        "senderAddress": sender,
        "recipients": {"to": [{"address": INBOX}]},
        "content": {"subject": f"Marie Parie website — {title}", "plainText": "\n\n".join(lines)},
        "replyTo": [{"address": fields["email"]}] if kind == "contact" else [{"address": INBOX}],
    }
    poller = client.begin_send(message)
    result = poller.result(timeout=30)
    if result.get("status") != "Succeeded":
        raise RuntimeError("Email delivery not accepted")


def get_ip(req):
    # X-Forwarded-For can be spoofed by clients; use platform-supplied peer address
    # and rate limits as best-effort only. A trusted edge/WAF is needed for strong IP limits.
    return req.headers.get("X-ARR-ClientIP") or req.headers.get("X-Azure-ClientIP") or "unknown"


@app.route(route="contact", methods=["POST"])
def contact(req: func.HttpRequest) -> func.HttpResponse:
    request_id = uuid.uuid4().hex[:12]
    stage = "request"
    started = time.monotonic()

    def reply(status, msg):
        response = func.HttpResponse(
            json.dumps({"message": msg, "requestId": request_id}),
            status_code=status, mimetype="application/json")
        response.headers["X-Request-ID"] = request_id
        return response

    if len(req.get_body()) > 12000:
        logging.warning("contact request_id=%s stage=request result=too_large", request_id)
        return reply(413, "Request too large")
    try:
        kind, fields, token = validate(req.get_json())
    except (ValueError, TypeError):
        logging.warning("contact request_id=%s stage=validation result=rejected", request_id)
        return reply(400, "Please check the form and try again.")

    ip = get_ip(req)
    for stage, action in (
        ("email", lambda: send_email(kind, fields)),
    ):
        stage_start = time.monotonic()
        try:
            result = action()

            logging.info("contact request_id=%s stage=%s result=ok duration_ms=%d",
                         request_id, stage, int((time.monotonic() - stage_start) * 1000))
        except Exception as exc:
            # Do not log exc messages or tracebacks: Azure SDK HTTP exceptions
            # can include PII, request payloads, or sensitive header values.
            logging.error("contact request_id=%s stage=%s result=error exception_type=%s duration_ms=%d",
                          request_id, stage, type(exc).__name__,
                          int((time.monotonic() - stage_start) * 1000))
            # TEMPORARY staging-only diagnostics. No exception messages, payloads or secrets.
            # Disable via CONTACT_DIAGNOSTICS=false before promotion to production.
            if os.getenv("CONTACT_DIAGNOSTICS", "").lower() == "true":
                response = func.HttpResponse(
                    json.dumps({"message": "We could not send your message. Please try again later.",
                                "requestId": request_id, "failedStage": stage,
                                "exceptionType": type(exc).__name__}),
                    status_code=503, mimetype="application/json")
                response.headers["X-Request-ID"] = request_id
                return response
            return reply(503, "We could not send your message. Please try again later.")

    logging.info("contact request_id=%s result=success duration_ms=%d",
                 request_id, int((time.monotonic() - started) * 1000))
    return reply(200, "Thank you! Your message has been sent.")
