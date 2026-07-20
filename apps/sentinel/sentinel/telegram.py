from __future__ import annotations

import json
import urllib.request

from .config import TelegramConfig


class TelegramNotifier:
    def __init__(self, config: TelegramConfig) -> None:
        self.config = config

    @property
    def enabled(self) -> bool:
        return bool(self.config.bot_token and self.config.chat_id)

    def send(self, text: str) -> bool:
        if not self.enabled:
            return False
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        body = json.dumps(
            {
                "chat_id": self.config.chat_id,
                "text": text,
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds):
            return True


def alert_text(title: str, description: str, occurrences: int) -> str:
    signal_label = "segnale" if occurrences == 1 else "segnali"
    return (
        "🚨 SENTINEL · ALLARME\n\n"
        f"{title}\n"
        f"{occurrences} {signal_label} richiedono attenzione.\n\n"
        f"{description}\n\n"
        "Stato: attivo"
    )


def recovery_text(title: str) -> str:
    return (
        "✅ SENTINEL · RIPRISTINATO\n\n"
        f"{title}\n"
        "Tutti i segnali correlati sono tornati regolari."
    )
