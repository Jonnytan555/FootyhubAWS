from abc import abstractmethod, ABC

import pandas as pd


class ResponseHandler(ABC):

    def __init__(self, data_path: str) -> None:
        self.data_path = data_path

    @abstractmethod
    def handle(self, response: str) -> pd.DataFrame:
        pass