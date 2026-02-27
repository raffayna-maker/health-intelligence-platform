"""
Email Poller — watches Gmail inbox and routes emails by subject prefix.

PROMPT: <title>
  Body = question sent to Clinical Assistant API → reply with LLM answer

REDTEAM: <any label>
  Body = promptfoo CLI command copied from PF SaaS UI
  → validates command starts with "promptfoo redteam run"
  → immediate reply: "scan started"
  → background thread runs scan → follow-up reply on completion
"""
import email as email_lib
import imaplib
import os
import smtplib
import subprocess
import threading
import time
from email.mime.text import MIMEText

import requests

GMAIL      = os.environ["GMAIL_ADDRESS"]
PASSWD     = os.environ["GMAIL_APP_PASSWORD"]
INTERVAL   = int(os.environ.get("GMAIL_POLL_INTERVAL", "60"))
BACKEND    = "http://backend:8080"
IMAP_HOST  = "imap.gmail.com"
SMTP_HOST  = "smtp.gmail.com"
SMTP_PORT  = 587


# ---------------------------------------------------------------------------
# SMTP helper
# ---------------------------------------------------------------------------

def send_reply(to: str, subject: str, body: str) -> None:
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"]    = GMAIL
    msg["To"]      = to
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls()
            s.login(GMAIL, PASSWD)
            s.send_message(msg)
        print(f"[reply] sent to {to}: {subject}")
    except Exception as e:
        print(f"[reply] SMTP error sending to {to}: {e}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def prompt_handler(body: str, sender: str, subject: str) -> None:
    print(f"[PROMPT] from={sender} body_preview={body[:80]!r}")
    try:
        r = requests.post(
            f"{BACKEND}/api/assistant/query",
            json={"question": body, "use_rag": True},
            timeout=120,
        )
        r.raise_for_status()
        answer = r.json().get("answer") or "(no answer returned)"
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


def handle(raw: bytes) -> None:
    msg     = email_lib.message_from_bytes(raw)
    subject = (msg.get("Subject") or "").strip()
    sender  = msg.get("From") or ""
    body    = get_body(msg)

    subject_upper = subject.upper()

    if subject_upper.startswith("PROMPT:"):
        prompt_handler(body, sender, subject)
    elif subject_upper.startswith("REDTEAM:"):
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
                _, data = imap.search(None, "UNSEEN")
                ids = data[0].split()
                if ids:
                    print(f"[poller] {len(ids)} unseen message(s)")
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
