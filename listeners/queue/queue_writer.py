from abc import ABC, abstractmethod


class QueueWriter(ABC):
    @abstractmethod
    def write(self, rows: list[dict]) -> None:
        """Write rows to the queue."""
