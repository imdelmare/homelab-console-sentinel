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
        body = json.dumps({"chat_id": self.config.chat_id, "text": text}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds):
            return True


def alert_text(title: str, description: str, occurrences: int) -> str:
    return f"[Sentinel] ALERT: {title}\n{description}\nOccurrences: {occurrences}"


def recovery_text(title: str) -> str:
    return f"[Sentinel] RECOVERY: {title}"
