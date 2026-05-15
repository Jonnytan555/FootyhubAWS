import time
import logging
import stomp

from typing import Callable
from listeners.queue.queue_reader import QueueConsumer
from listeners.queue.mq.batch_listener import BatchListener
from listeners.queue.mq.queue_listener import QueueListener


class ActiveMQQueueConsumer(QueueConsumer):
    """
    Reads messages from an ActiveMQ queue via STOMP.

    Uses client-individual ACK mode so messages are only removed from the broker
    after mark_processed() or mark_failed() is called. The connection stays open
    between read() and settlement — disconnect happens after both mark_* calls.
    """

    def __init__(
        self,
        host: str,
        port: int,
        destination: str,
        username: str = "",
        password: str = "",
        max_messages: int = 50,
        timeout_secs: float = 5.0,
        listener_factory: Callable[[list, int], QueueListener] = BatchListener,
    ) -> None:
        self.host = host
        self.port = port
        self.destination = destination
        self.username = username
        self.password = password
        self.max_messages = max_messages
        self.timeout_secs = timeout_secs
        self.listener_factory = listener_factory
        self._conn: stomp.Connection | None = None
        self._settle_calls = 0

    def read(self) -> list[dict]:
        self._settle_calls = 0
        received: list[tuple[str, dict]] = []

        conn = stomp.Connection([(self.host, self.port)])

        listener = self.listener_factory(received, self.max_messages)

        conn.set_listener("", listener)
        conn.connect(self.username, self.password, wait=True)
        conn.subscribe(destination=self.destination, id=1, ack="client-individual")

        deadline = time.monotonic() + self.timeout_secs
        while time.monotonic() < deadline and not listener.done:
            time.sleep(0.1)

        self._conn = conn
        logging.info("ActiveMQ read %d messages from %s", len(received), self.destination)

        return [{**body, "_stomp_message_id": msg_id} for msg_id, body in received]

    def mark_processed(self, items: list[dict]) -> None:
        for item in items:
            if msg_id := item.get("_stomp_message_id"):
                self._conn.ack(msg_id, "1")
        self._maybe_disconnect()

    def mark_failed(self, items: list[dict]) -> None:
        for item in items:
            if msg_id := item.get("_stomp_message_id"):
                self._conn.nack(msg_id, "1")
        self._maybe_disconnect()

    def _maybe_disconnect(self) -> None:
        self._settle_calls += 1
        if self._settle_calls >= 2 and self._conn:
            self._conn.disconnect()
            self._conn = None
