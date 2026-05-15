from abc import ABC, abstractmethod


class QueueReader(ABC):
    @abstractmethod
    def read(self) -> list[dict]:
        """Read pending items from the queue and return as a list of dicts."""


class QueueConsumer(QueueReader):
    """
    Extended reader for queues that require explicit acknowledgement after processing.
    Implementations receive the full item dicts so they can extract whichever
    identifier they need (e.g. SQL row ID, STOMP message ID).
    """

    @abstractmethod
    def mark_processed(self, items: list[dict]) -> None:
        """Acknowledge items as successfully processed."""

    @abstractmethod
    def mark_failed(self, items: list[dict]) -> None:
        """Acknowledge items as failed so they can be retried or dead-lettered."""
