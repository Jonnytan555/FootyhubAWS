import json
import logging

import stomp

from listeners.queue.mq.queue_listener import QueueListener


class BatchListener(stomp.ConnectionListener, QueueListener):
    def __init__(self, received: list, max_messages: int) -> None:
        self.received = received
        self.max_messages = max_messages
        self._done = False

    @property
    def done(self) -> bool:
        return self._done

    def on_message(self, frame) -> None:
        body = json.loads(frame.body)
        self.received.append((frame.headers["message-id"], body))
        if len(self.received) >= self.max_messages:
            self._done = True

    def on_error(self, frame) -> None:
        logging.error("ActiveMQ error: %s", frame.body)
