from abc import ABC, abstractmethod


class QueueListener(ABC):
    @abstractmethod
    def on_message(self, frame) -> None: ...

    @abstractmethod
    def on_error(self, frame) -> None: ...

    @property
    @abstractmethod
    def done(self) -> bool: ...
