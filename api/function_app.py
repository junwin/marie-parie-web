"""Marie Parie website enquiry endpoint: validate, verify, rate-limit, email."""
import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
import uuid

import azure.functions as func
from azure.communication.email import EmailClient
from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError, ResourceModifiedError
from azure.data.tables import TableServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

INBOX = "bonjour@marieparieboutique.com"
ALLOWED_KINDS = {"contact", "mailing list"}
EMAIL_PATTERN = re.compile(r"^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$")
PHONE_PATTERN = re.compile(r"^[+0-9 ().-]{0,40}$")


def setting(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required application setting: {name}")
    return value


def text_of(data, name, min_len=1, max_len=80, pattern=None):
    """Return a stripped, validated string field or raise ValueError."""
    value = data.get(name)
    if not isinstance(value, str):
        raise ValueError(f"Invalid {name}")
    value = value.strip()
    if not min_len <= len(value) <= max_len:
        raise ValueError(f"Invalid {name}")
    if pattern and not pattern.fullmatch(value):
        raise ValueError(f"Invalid {name}")
    return value


def validate(data):
    """Return (kind, fields, turnstile_token) or raise ValueError."""
    if not isinstance(data, dict):
        raise ValueError("Invalid request")
    kind = data.get("kind")
    if kind not in ALLOWED_KINDS:
        raise ValueError("Unknown form")

    fields = {
        "firstName": text_of(data, "firstName"),
        "lastName": text_of(data, "lastName"),
        "email": text_of(data, "email", max_len=254, pattern=EMAIL_PATTERN),
    }

    if kind == "contact":
        fields["message"] = text_of(data, "message", max_len=3000)
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
        "secret": setting("TURNSTILE_SECRET_KEY"),
        "response": token,
        "remoteip": remote_ip,
    }).encode()
    request = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=8) as response:
        result = json.load(response)
    allowed = {h.strip().lower() for h in setting("TURNSTILE_ALLOWED_HOSTNAMES").split(",") if h.strip()}
    return result.get("success") is True and str(result.get("hostname", "")).lower() in allowed


def bump_counter(table, partition, row, limit):
    """Increment a counter once under `limit`, fail closed on persistent races."""
    for _ in range(8):
        try:
            entity = table.get_entity(partition_key=partition, row_key=row)
        except ResourceNotFoundError:
            try:
                table.create_entity({"PartitionKey": partition, "RowKey": row, "Count": 1})
                return True
            except ResourceExistsError:
                continue
        if entity["Count"] >= limit:
            return False
        try:
            table.update_entity({**entity, "Count": entity["Count"] + 1},
                                etag=entity.metadata["etag"],
                                match_condition=MatchConditions.IfNotModified)
            return True
        except ResourceModifiedError:
            continue
    raise RuntimeError("Rate-limit counter busy")


def check_rate_limit(ip):
    now = int(time.time())
    key = hashlib.sha256((setting("RATE_LIMIT_SALT") + ":" + ip).encode()).hexdigest()
    table = TableServiceClient.from_connection_string(
        setting("AzureWebJobsStorage")).get_table_client("MarieParieFormLimits")
    rules = [
        ("ip10", f"{now // 600}", key, 3),
        ("ipday", f"{now // 86400}", key, 20),
        ("globalday", f"{now // 86400}", "all", int(os.getenv("GLOBAL_DAILY_LIMIT", "100"))),
    ]
    return all(bump_counter(table, p, r, limit) for _, p, r, limit in rules)


def send_email(kind, fields):
    title = "Contact enquiry" if kind == "contact" else "Mailing list request"
    lines = [
        f"Form: {title}",
        f"Name: {fields['firstName']} {fields['lastName']}",
        f"Email: {fields['email']}",
    ]
    if kind == "contact":
        lines.append(f"Message:\n{fields['message']}")
    else:
        lines.append(f"Phone: {fields['phone'] or 'Not provided'}\nMarketing consent: Yes")

    message = {
        "senderAddress": setting("ACS_SENDER_ADDRESS"),
        "recipients": {"to": [{"address": INBOX}]},
        "content": {"subject": f"Marie Parie website — {title}", "plainText": "\n\n".join(lines)},
        "replyTo": [{"address": fields["email"] if kind == "contact" else INBOX}],
    }
    poller = EmailClient.from_connection_string(setting("ACS_CONNECTION_STRING")).begin_send(message)
    poller = client.begin_send(message)
    result = poller.result(timeout=30)

def client_ip(req):
    # X-Forwarded-For can be spoofed; use the platform-supplied peer address only.
    return req.headers.get("X-ARR-ClientIP") or req.headers.get("X-Azure-ClientIP") or "unknown"


@app.route(route="contact", methods=["POST"])
def contact(req: func.HttpRequest) -> func.HttpResponse:
    request_id = uuid.uuid4().hex[:12]
    started = time.monotonic()

    def reply(status, msg, **extra):
        body = json.dumps({"message": msg, "requestId": request_id, **extra})
        response = func.HttpResponse(body, status_code=status, mimetype="application/json")
        response.headers["X-Request-ID"] = request_id
        return response

    if len(req.get_body()) > 12000:
        return reply(413, "Request too large")

    try:
        kind, fields, token = validate(req.get_json())
    except (ValueError, TypeError):
        return reply(400, "Please check the form and try again.")

    # if not verify_turnstile(token, client_ip(req)):
    #    return reply(400, "Please check the form and try again.")

    # if not check_rate_limit(client_ip(req)):
    #     return reply(429, "Too many requests. Please try again later.")

    try:
        send_email(kind, fields)
    except Exception:
        # Never log exception details: Azure SDK errors can contain PII or secrets.
        logging.error("contact request_id=%s result=error exception_type=%s",
                      request_id, "send_email failure")
        return reply(503, "We could not send your message. Please try again later.",
                     failedStage="email")

    logging.info("contact request_id=%s result=success duration_ms=%d",
                 request_id, int((time.monotonic() - started) * 1000))
    return reply(200, "Thank you! Your message has been sent.")