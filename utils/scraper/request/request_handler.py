from abc import ABC

from requests import Response


class RequestHandler(ABC):
    def __init__(
            self, url: str, params=None, headers=None, auth=None, timeout: int = 120):
        self.url = url
        self.params = params
        self.headers = headers if headers else headers
        self.auth = auth
        self.timeout = timeout

    def handle(self) -> Response:
        """Abstract method to handle request"""

    def get_default_headers(self):
        """Default User-Agent headers for request"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
        }




