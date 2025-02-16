import logging
from app import app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server")
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logger.error("Failed to start Flask server: %s", str(e))
        raise