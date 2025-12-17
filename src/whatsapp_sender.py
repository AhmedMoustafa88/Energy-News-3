"""
WhatsApp sender using Twilio.

This module formats a WhatsApp-friendly digest of news articles and sends it to one
or more recipients via the Twilio WhatsApp API.

Environment variables (see .env.example):
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_WHATSAPP_NUMBER       (e.g., whatsapp:+14155238886)
- WHATSAPP_PHONE_NUMBERS       (comma-separated E.164 numbers; e.g., +2010..., +971...)
Optional:
- WHATSAPP_MAX_CHARS_PER_MSG   (default: 1400)
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from twilio.rest import Client
except Exception:  # pragma: no cover
    Client = None


class WhatsAppSender:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", "").strip()
        self.recipients_raw = os.getenv("WHATSAPP_PHONE_NUMBERS", "").strip()
        self.max_chars = int(os.getenv("WHATSAPP_MAX_CHARS_PER_MSG", "1400"))

        self._client = None
        if self.account_sid and self.auth_token and Client:
            self._client = Client(self.account_sid, self.auth_token)

    @staticmethod
    def _to_whatsapp_addr(number: str) -> str:
        number = (number or "").strip()
        if not number:
            return ""
        if number.startswith("whatsapp:"):
            return number
        return f"whatsapp:{number}"

    def _recipients(self) -> List[str]:
        if not self.recipients_raw:
            return []
        parts = [p.strip() for p in self.recipients_raw.split(",") if p.strip()]
        return [self._to_whatsapp_addr(p) for p in parts if p]

    @staticmethod
    def _safe(s: Any) -> str:
        return (str(s) if s is not None else "").strip()

    @staticmethod
    def _format_date(s: str) -> str:
        """Best-effort normalization of published_at."""
        s = (s or "").strip()
        if not s:
            return ""
        # Keep original if parsing fails; avoids hard dependency.
        try:
            # Common formats: ISO 8601 with Z, RFC 3339, etc.
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return s

    def format_message(self, articles: List[Dict], analysis: str = "") -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        header = [
            f"Electricity Meters & Grid News Digest",
            f"Generated: {now}",
            ""
        ]

        if not articles:
            body = ["No new news items found for the selected period."]
            if analysis:
                body += ["", "AI Notes:", analysis.strip()]
            return "\n".join(header + body).strip()

        lines = []
        for i, a in enumerate(articles, start=1):
            title = self._safe(a.get("title", "Untitled"))
            url = self._safe(a.get("url", ""))
            source = self._safe(a.get("source", ""))
            fetched_from = self._safe(a.get("fetched_from", ""))
            published_at = self._format_date(self._safe(a.get("published_at", "")))

            meta_parts = [p for p in [source, fetched_from, published_at] if p]
            meta = " | ".join(meta_parts)

            lines.append(f"{i}. {title}")
            if meta:
                lines.append(f"   {meta}")
            if url:
                lines.append(f"   {url}")
            lines.append("")  # spacer

        if analysis and analysis.strip():
            lines.append("AI Notes:")
            lines.append(analysis.strip())
            lines.append("")

        msg = "\n".join(header + lines).strip()
        return msg

    def _split_message(self, message: str) -> List[str]:
        message = message or ""
        if len(message) <= self.max_chars:
            return [message]

        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        # Split by lines first to keep readability.
        for line in message.splitlines():
            add_len = len(line) + 1  # + newline
            if current and (current_len + add_len) > self.max_chars:
                chunks.append("\n".join(current).strip())
                current = [line]
                current_len = len(line) + 1
            else:
                current.append(line)
                current_len += add_len

        if current:
            chunks.append("\n".join(current).strip())

        # Safety: never return empty.
        return [c for c in chunks if c] or [message[: self.max_chars]]

    def send(self, message: str) -> Dict[str, Any]:
        """Send message via Twilio WhatsApp. Returns a result dict."""
        recipients = self._recipients()
        if not recipients:
            return {"status": "skipped", "reason": "No WHATSAPP_PHONE_NUMBERS configured", "sent": 0}

        if not self._client:
            missing = []
            if not self.account_sid:
                missing.append("TWILIO_ACCOUNT_SID")
            if not self.auth_token:
                missing.append("TWILIO_AUTH_TOKEN")
            if not self.from_number:
                missing.append("TWILIO_WHATSAPP_NUMBER")
            if not Client:
                missing.append("twilio package import failed")
            return {"status": "skipped", "reason": f"Twilio not configured: {', '.join(missing)}", "sent": 0}

        from_addr = self._to_whatsapp_addr(self.from_number)
        chunks = self._split_message(message)

        results = {"status": "ok", "sent": 0, "details": []}

        for to_addr in recipients:
            for idx, chunk in enumerate(chunks, start=1):
                try:
                    msg = self._client.messages.create(
                        from_=from_addr,
                        to=to_addr,
                        body=chunk if len(chunks) == 1 else f"({idx}/{len(chunks)})\n{chunk}"
                    )
                    results["sent"] += 1
                    results["details"].append({"to": to_addr, "sid": getattr(msg, "sid", None), "chunk": idx})
                except Exception as e:
                    results["status"] = "partial_fail"
                    results["details"].append({"to": to_addr, "error": str(e), "chunk": idx})

        return results
