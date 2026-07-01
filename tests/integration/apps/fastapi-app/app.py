import logging
import random

from fastapi import FastAPI

# Configure the app's logging at DEBUG. Under instrumentation the agent must preserve this level.
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/rolldice")
def rolldice():
    logger.debug("FASTAPI-DEBUG-OK")
    return str(random.randint(1, 6))
