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

DB_SERVER = "localhost"
DB_NAME   = "FootyHub"
DB_DRIVER = "ODBC Driver 17 for SQL Server"
