from apscheduler.triggers.cron import CronTrigger

import runners.run_publisher as publisher
from runners.config.appsettings import SCHEDULE_HOURS

JOB_ID   = "publisher"
JOB_NAME = "Fetch articles from Perplexity → article_queue"
TRIGGER  = CronTrigger(hour=SCHEDULE_HOURS, minute=0)
RUN      = publisher.run
