from apscheduler.triggers.cron import CronTrigger

import runners.run_subscriber as subscriber
from runners.config.appsettings import SCHEDULE_HOURS, SCHEDULE_GAP_MINS

JOB_ID   = "subscriber"
JOB_NAME = "Enrich article_queue with Claude → articles"
TRIGGER  = CronTrigger(hour=SCHEDULE_HOURS, minute=SCHEDULE_GAP_MINS)
RUN      = subscriber.run
