from scraper.persistence import PersistenceHandler
from scraper.request.request_handler import RequestHandler
from scraper.response.response_handler import ResponseHandler


class Scraper:
    def __init__(self,
                 request_handler: RequestHandler,
                 response_handler: ResponseHandler,
                 persist_handler: PersistenceHandler):
        self.request_handler = request_handler
        self.response_handler = response_handler
        self.persist_handler = persist_handler

    def scrape(self, dropNa=False, dtype=None, created_at="CreatedAt"):

        response = self.request_handler.handle()

        result = self.response_handler.handle(response)

        return self.persist_handler.handle(result, dropNa, dtype, created_at)

