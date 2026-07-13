from __future__ import annotations

import logging
import signal
import time

from .checks import check_heartbeat, check_http_target
from .config import SentinelConfig
from .heartbeat import HeartbeatServer
from .store import IncidentChange, Observation, SentinelStore
from .telegram import TelegramNotifier, alert_text, recovery_text

LOG = logging.getLogger("sentinel")


class SentinelService:
    def __init__(self, config: SentinelConfig, notifier: TelegramNotifier | None = None) -> None:
        self.config = config
        self.store = SentinelStore(config.state_path)
        self.notifier = notifier or TelegramNotifier(config.telegram)
        self._stop = False
        self._heartbeat_server = HeartbeatServer(
            config.listen_host,
            config.listen_port,
            config.heartbeat_token,
            self.store,
        )

    def run_once(self) -> list[IncidentChange]:
        changes: list[IncidentChange] = []
        for target in self.config.targets:
            changes.extend(self._handle_observation(check_http_target(target)))
        for heartbeat in self.config.heartbeats:
            changes.extend(self._handle_observation(check_heartbeat(heartbeat, self.store)))
        return changes

    def serve_forever(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
        self._install_signal_handlers()
        self._heartbeat_server.start()
        LOG.info(
            "sentinel started targets=%s heartbeats=%s heartbeat_listener=%s:%s",
            len(self.config.targets),
            len(self.config.heartbeats),
            self.config.listen_host,
            self.config.listen_port,
        )
        try:
            while not self._stop:
                self.run_once()
                time.sleep(max(5, self.config.loop_interval_seconds))
        finally:
            self._heartbeat_server.stop()

    def _handle_observation(self, observation: Observation) -> list[IncidentChange]:
        if observation.ok:
            change = self.store.record_recovery(observation)
            if change is None:
                return []
            self._notify_recovery(change)
            return [change]

        change = self.store.record_failure(observation)
        if change.action == "opened":
            self._notify_alert(change)
        return [change]

    def _notify_alert(self, change: IncidentChange) -> None:
        LOG.warning("%s: %s", change.observation.title, change.observation.description)
        try:
            self.notifier.send(
                alert_text(
                    change.observation.title,
                    change.observation.description,
                    change.occurrences,
                )
            )
        except Exception as exc:  # noqa: BLE001 - keep alert loop alive; never log token-bearing URLs.
            LOG.warning("telegram alert delivery failed: %s", type(exc).__name__)

    def _notify_recovery(self, change: IncidentChange) -> None:
        LOG.info("recovered: %s", change.observation.title)
        try:
            self.notifier.send(recovery_text(change.observation.title))
        except Exception as exc:  # noqa: BLE001
            LOG.warning("telegram recovery delivery failed: %s", type(exc).__name__)

    def _install_signal_handlers(self) -> None:
        def stop(_signum: int, _frame: object) -> None:
            self._stop = True

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
