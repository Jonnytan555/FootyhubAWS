import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from api.web.routes import router

_DIR     = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(_DIR, "logs")
os.makedirs(LOG_PATH, exist_ok=True)

app = FastAPI()
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host="127.0.0.1", port=8001, reload=False)
