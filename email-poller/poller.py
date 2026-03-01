"""
Email Poller — watches Gmail inbox and routes emails by subject prefix.

PROMPT (or PROMPT: anything, or RE: PROMPT from replies)
  Body = question sent to Clinical Assistant API → reply with LLM answer
  Each sender gets a persistent conversation session (visible in the UI
  under the 'anonymous' user / Admin tab).

REDTEAM (or REDTEAM: anything)
  Body = promptfoo CLI command copied from PF SaaS UI
  → validates command starts with "promptfoo redteam run"
  → immediate reply: "scan started"
  → background thread runs scan → follow-up reply on completion
"""
import email as email_lib
import imaplib
import os
import re
import smtplib
import subprocess
import threading
import time
import uuid
from datetime import date
from email.header import decode_header as _decode_header
from email.mime.text import MIMEText

import requests

GMAIL      = os.environ["GMAIL_ADDRESS"]
PASSWD     = os.environ["GMAIL_APP_PASSWORD"]
INTERVAL   = int(os.environ.get("GMAIL_POLL_INTERVAL", "60"))
BACKEND    = "http://backend:8080"
IMAP_HOST  = "imap.gmail.com"
SMTP_HOST  = "smtp.gmail.com"
SMTP_PORT  = 587

# In-memory map: sender address → session UUID
# Persists for the lifetime of the container so replies and follow-up
# emails from the same sender continue in the same conversation session.
_sender_sessions: dict = {}


def _session_for(sender: str) -> str:
    """Return the persistent session UUID for this sender, creating one if needed."""
    if sender not in _sender_sessions:
        _sender_sessions[sender] = str(uuid.uuid4())
        print(f"[session] new session {_sender_sessions[sender]} for {sender}")
    return _sender_sessions[sender]


# ---------------------------------------------------------------------------
# SMTP helper
# ---------------------------------------------------------------------------

def send_reply(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"]    = GMAIL
    msg["To"]      = to
    print(f"[reply] attempting SMTP send to={to!r} subject={subject!r}")
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.set_debuglevel(0)
            s.starttls()
            s.login(GMAIL, PASSWD)
            refused = s.send_message(msg)
            if refused:
                print(f"[reply] WARNING — some recipients refused: {refused}")
            else:
                print(f"[reply] SUCCESS — sent to {to}")
    except smtplib.SMTPException as e:
        print(f"[reply] SMTP ERROR: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"[reply] ERROR: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def prompt_handler(body: str, sender: str, subject: str) -> None:
    question = extract_prompt(body)
    session_id = _session_for(sender)
    print(f"[PROMPT] from={sender} session={session_id} question_preview={question[:80]!r}")
    try:
        r = requests.post(
            f"{BACKEND}/api/assistant/query",
            json={"question": question, "use_rag": True, "session_id": session_id},
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("blocked"):
            blocked_by = data.get("blocked_by") or "security scan"
            reason = data.get("blocked_reason") or "Security scan failed"
            answer = f"Blocked by {blocked_by}\n\nBLOCKED: {reason}"
        else:
            answer = data.get("answer") or "(no answer returned)"
    except Exception as e:
        answer = f"Error querying assistant: {e}"
    send_reply(sender, f"RE: {subject}", answer)


def redteam_handler(body: str, sender: str, subject: str) -> None:
    # Extract the CLI command — first non-blank line of the body
    cmd_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), "")
    print(f"[REDTEAM] from={sender} cmd={cmd_line!r}")

    if not cmd_line.lower().startswith("promptfoo redteam run"):
        send_reply(
            sender,
            f"RE: {subject} — Invalid Command",
            "Could not start red team scan.\n\n"
            "The email body must start with:\n"
            "  promptfoo redteam run ...\n\n"
            "Copy the command from the PromptFoo SaaS UI and paste it as the email body.",
        )
        return

    # Immediate acknowledgement
    send_reply(
        sender,
        f"RE: {subject} — Scan Started",
        "Red team scan started. You will be notified when the scan is completed.",
    )

    # Run scan in background thread so the polling loop is not blocked
    def run_and_notify():
        print(f"[REDTEAM] starting subprocess: {cmd_line}")
        try:
            result = subprocess.run(
                cmd_line.split(),
                timeout=3600,           # 1-hour hard limit
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                send_reply(
                    sender,
                    f"RE: {subject} — Scan Completed",
                    "Red team scan completed successfully. "
                    "Check the PromptFoo dashboard for results.",
                )
            else:
                stderr_preview = (result.stderr or "")[:500]
                send_reply(
                    sender,
                    f"RE: {subject} — Scan Failed",
                    f"Red team scan exited with code {result.returncode}.\n\n"
                    f"Error output:\n{stderr_preview}",
                )
        except subprocess.TimeoutExpired:
            send_reply(
                sender,
                f"RE: {subject} — Scan Timed Out",
                "Red team scan timed out after 1 hour.",
            )
        except Exception as e:
            send_reply(
                sender,
                f"RE: {subject} — Scan Error",
                f"Unexpected error running scan:\n{e}",
            )
        print(f"[REDTEAM] subprocess finished for {sender}")

    t = threading.Thread(target=run_and_notify, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------

def extract_prompt(text: str) -> str:
    """Extract only the prompt from an email body, stripping signatures.

    Strategy (in order):
    1. Take only the first paragraph (text before the first blank line) —
       email clients always put the message before a blank line, then signature.
    2. If the first paragraph still contains an inline '-- ' signature marker,
       strip everything from ' -- ' onward as a fallback.
    """
    normalized = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    # Step 1: take only the first paragraph
    first_para = normalized.split('\n\n')[0].strip()
    # Step 2: also strip inline '-- ' marker (e.g. Gmail appends it without a newline)
    inline_idx = first_para.find(' -- ')
    if inline_idx != -1:
        first_para = first_para[:inline_idx].strip()
    return first_para


def get_body(msg) -> str:
    """Extract plain-text body from an email.Message object."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace").strip()
        return ""
    charset = msg.get_content_charset() or "utf-8"
    return msg.get_payload(decode=True).decode(charset, errors="replace").strip()


def decode_subject(raw_subject: str) -> str:
    """Decode RFC 2047-encoded email subject to a plain string."""
    parts = _decode_header(raw_subject or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded).strip()


def handle(raw: bytes) -> None:
    msg            = email_lib.message_from_bytes(raw)
    raw_subject    = msg.get("Subject") or ""
    subject        = decode_subject(raw_subject)
    sender         = msg.get("From") or ""
    body           = get_body(msg)

    # Strip RE:/FWD: prefixes so replies are handled the same as new emails
    clean_subject = re.sub(r'^(re|fwd?)\s*:\s*', '', subject.strip(), flags=re.IGNORECASE).strip()
    # Extract first word (split on spaces and colons)
    first_word = re.split(r'[\s:]+', clean_subject.upper())[0]

    if first_word == "PROMPT":
        prompt_handler(body, sender, subject)
    elif first_word == "REDTEAM":
        redteam_handler(body, sender, subject)
    else:
        print(f"[skip] unrecognised subject: {subject!r}")


# ---------------------------------------------------------------------------
# Polling loop
# ---------------------------------------------------------------------------

def poll() -> None:
    print(f"[poller] starting — account={GMAIL} interval={INTERVAL}s backend={BACKEND}")
    while True:
        try:
            with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
                imap.login(GMAIL, PASSWD)
                imap.select("INBOX")
                # Only fetch UNSEEN emails received today — avoids processing
                # the entire historical inbox on startup
                today = date.today().strftime("%d-%b-%Y")  # e.g. "27-Feb-2026"
                _, data = imap.search(None, "UNSEEN", f'SINCE "{today}"')
                ids = data[0].split()
                if ids:
                    print(f"[poller] {len(ids)} new unseen message(s) since {today}")
                for mid in ids:
                    try:
                        _, msg_data = imap.fetch(mid, "(RFC822)")
                        raw = msg_data[0][1]
                        handle(raw)
                    except Exception as e:
                        print(f"[poller] error handling message {mid}: {e}")
                    finally:
                        imap.store(mid, "+FLAGS", "\\Seen")
        except Exception as e:
            print(f"[poller] connection error: {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    poll()
