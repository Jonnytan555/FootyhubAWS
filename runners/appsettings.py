import os
from dotenv import load_dotenv
load_dotenv()

SOURCE_NAME = "FootballNewsSites"
SOURCE_TYPE = "football"

SEARCH_MODEL          = "sonar-pro"
MAX_RESULTS_PER_TOPIC = 10
MIN_CITATION_LENGTH   = 80
SEEN_URL_EXPIRY_DAYS  = 3

ENRICH_MODEL = "claude-haiku-4-5"

SCHEDULE_HOURS    = "0,6,12,18"
SCHEDULE_GAP_MINS = 15

APP_NAME = "footyhub"

SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
AWS_REGION    = os.environ.get("AWS_REGION", "eu-west-2")
