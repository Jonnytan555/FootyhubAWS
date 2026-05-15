import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

import runners.config.appsettings as settings
import logger as logger

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from runners.scheduler import publisher_job, subscriber_job

logger.setup_log(
    app=settings.APP_NAME,
    filename=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", settings.APP_NAME + "_scheduler.log"),
    use_stream=True,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

load_dotenv()

_JOBS = [publisher_job, subscriber_job]


def main():
    scheduler = BlockingScheduler()

    for job in _JOBS:
        scheduler.add_job(
            job.RUN,
            job.TRIGGER,
            id=job.JOB_ID,
            name=job.JOB_NAME,
            misfire_grace_time=300,
        )
        logging.info("Registered job: %s", job.JOB_NAME)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logging.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
