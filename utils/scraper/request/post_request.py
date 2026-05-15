import httpx

from scraper.request.request_handler import RequestHandler
from stomp import logging


class HttpPostRequestHandler(RequestHandler):
    def __init__(
            self,
            url: str,
            params = None,
            json = None,
            data=None,
            headers = None,
            auth = None,
            timeout: int = 120
    ) -> None:
        super().__init__(url, params, headers, auth, timeout=timeout)
        self.json = json
        self.data = data

    def handle(self):
        try:
            logging.info(
                "[POST ]Requesting from url %s with body %s...",
                self.url,
                self.json or self.data,
            )
            response = response = httpx.request(
                    method="POST",
                    url=self.url,
                    params=self.params,
                    json=self.json,
                    data=self.data,
                    headers=self.headers,
                    auth=self.auth,
                    timeout=self.timeout
            )

            response.raise_for_status()

        except Exception as e:
            logging.error(
                "An error occurred while getting data from %s. Exception: %s",
                self.url,
                repr(e),
            )
            raise e
