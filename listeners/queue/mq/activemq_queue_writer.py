import json
import logging
import stomp

from listeners.queue.queue_writer import QueueWriter


class ActiveMQQueueWriter(QueueWriter):
    """Publishes articles to an ActiveMQ queue via STOMP."""

    def __init__(
        self,
        host: str,
        port: int,
        destination: str,
        username: str = "",
        password: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.destination = destination
        self.username = username
        self.password = password

    def write(self, rows: list[dict]) -> None:
        if not rows:
            return

        conn = stomp.Connection([(self.host, self.port)])
        conn.connect(self.username, self.password, wait=True)

        for row in rows:
            conn.send(
                destination=self.destination,
                body=json.dumps(row, default=str),
                content_type="application/json",
            )

        conn.disconnect()
        logging.info("ActiveMQ published %d messages to %s", len(rows), self.destination)
