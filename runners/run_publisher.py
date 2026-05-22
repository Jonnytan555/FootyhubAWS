import logging
import os
import sys
import traceback
from pathlib import Path
from time import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.logging.logger as logger
import runners.appsettings as settings
from utils.db.db_access import build_engine
from listeners.article_pipeline import ArticlePipeline
from listeners.read.perplexity_search import PerplexitySearch
from listeners.transform.article_mapper import FootballArticleMapper
from listeners.queue.sqs.sqs_queue_writer import SQSQueueWriter
from runners.ai.topics import FOOTBALL_TOPICS
from dotenv import load_dotenv

_DIR           = os.path.dirname(os.path.abspath(__file__))
LOG_PATH       = os.path.join(_DIR, "logs")
SEEN_URLS_PATH = os.path.join(_DIR, "seen_urls.json")
PROMPT_PATH    = Path(_DIR) / "ai" / "football_search_prompt.txt"
engine         = build_engine()

logger.setup_log(
    app=settings.APP_NAME,
    filename=os.path.join(LOG_PATH, settings.APP_NAME + "_publisher.log"),
    use_stream=True,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)

load_dotenv()


def run():
    try:
        start = time()

        ArticlePipeline(
            reader=PerplexitySearch(
                api_key=os.environ["PERPLEXITY_API_KEY"],
                topics=FOOTBALL_TOPICS,
                model=settings.SEARCH_MODEL,
                max_results_per_topic=settings.MAX_RESULTS_PER_TOPIC,
                min_citation_length=settings.MIN_CITATION_LENGTH,
                seen_urls_path=SEEN_URLS_PATH,
                seen_url_expiry_days=settings.SEEN_URL_EXPIRY_DAYS,
                prompt_path=PROMPT_PATH,
                extra_blocked_domains={"mancity.com"},
            ),
            enricher=FootballArticleMapper(source_name=settings.SOURCE_NAME, source_type=settings.SOURCE_TYPE),
            writer=SQSQueueWriter(
                queue_url=os.environ["SQS_QUEUE_URL"],
                region=os.environ.get("AWS_REGION", "eu-west-2"),
            ),
        ).run()

        logging.info(f"Finished {settings.APP_NAME} publisher. Duration: {time() - start:.1f}s")

    except Exception as e:
        logging.error([e, traceback.format_exc()])
        raise


if __name__ == "__main__":
    run()
