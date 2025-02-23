import logging
from app import app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure OpenAI API key and Pinecone API key are set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server")
        app.run(host="0.0.0.0", port=5000)
    except Exception as e:
        logger.error("Failed to start Flask server: %s", str(e))
        raise