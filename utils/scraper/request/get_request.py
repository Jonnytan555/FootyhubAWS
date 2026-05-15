import logging
import httpx

from scraper.request.request_handler import RequestHandler

class HttpGetRequestHandler(RequestHandler):

    def handle(self):
        try:
            logging.info(
                "[GET] Requesting from url %s with params %s...",
                self.url,
                self.params
            )

            response = httpx.request(
                method="GET",
                url=self.url,
                headers=self.headers,
                params=self.params,
                auth=self.auth,
                timeout=self.timeout,
            )

            response.raise_for_status()
            return response

        except Exception as e:
            logging.error(
                "An error occurred while getting data from %s. Exception: %s",
                self.url,
                repr(e),
            )
            raise e
