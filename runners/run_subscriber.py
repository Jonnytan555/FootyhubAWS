import logging
import os
import sys
import traceback
from time import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.logging.logger as logger
import runners.appsettings as settings
from utils.db.db_access import build_engine

_DIR     = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(_DIR, "logs")
engine   = build_engine()

from listeners.article_pipeline import ArticlePipeline
from listeners.queue.sqs.sqs_queue_consumer import SQSQueueConsumer
from listeners.enrich.enricher import Enricher
from listeners.save.article_writer import ArticleWriter
from runners.ai.taxonomy import FOOTBALL_TREE
from dotenv import load_dotenv

logger.setup_log(
    app=settings.APP_NAME,
    filename=os.path.join(LOG_PATH, settings.APP_NAME + "_subscriber.log"),
    use_stream=True,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)

load_dotenv()


def run():
    try:
        start = time()

        ArticlePipeline(
            reader=SQSQueueConsumer(
                queue_url=os.environ["SQS_QUEUE_URL"],
                region=os.environ.get("AWS_REGION", "eu-west-2"),
            ),
            enricher=Enricher(
                api_key=os.environ["ANTHROPIC_API_KEY"],
                taxonomy=FOOTBALL_TREE,
                model=settings.ENRICH_MODEL,
            ),
            writer=ArticleWriter(engine=engine),
        ).run()

        logging.info(f"Finished {settings.APP_NAME} subscriber. Duration: {time() - start:.1f}s")

    except Exception as e:
        logging.error([e, traceback.format_exc()])
        raise


if __name__ == "__main__":
    run()
