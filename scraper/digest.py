import os
import smtplib
from email.mime.text import MIMEText
from html import escape


def send_digest(jobs):
    """Email new high-scoring jobs. Needs SMTP_USER, SMTP_PASS, DIGEST_TO (Gmail app password works)."""
    user, pw, to = os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASS"), os.environ.get("DIGEST_TO")
    if not (user and pw and to):
        print("[digest] skipped (no SMTP secrets)")
        return
    if not jobs:
        print("[digest] nothing new above threshold")
        return
    rows = "".join(
        f"<p><b>{j['score']}</b> &middot; <span style='color:#0b6e4f'>{escape(j['path'])}</span> &middot; "
        f"<a href='{escape(j['url'])}'>{escape(j['title'])}</a> at {escape(j['company'])}<br>"
        f"<small>{escape(j['location'])} &middot; {escape(j['source'])}"
        f"{' &middot; ' + escape(j['llm']['why']) if j.get('llm') else ''}</small></p>"
        for j in jobs[:25])
    msg = MIMEText(f"<h3>{len(jobs)} new matches</h3>{rows}", "html")
    msg["Subject"] = f"Job board: {len(jobs)} new matches"
    msg["From"], msg["To"] = user, to
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(user, pw)
        s.sendmail(user, [to], msg.as_string())
    print(f"[digest] sent {len(jobs)} jobs to {to}")