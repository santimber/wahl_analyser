import os
import logging
from dotenv import load_dotenv  # Load .env variables
from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rag_engine import analyze_statement

# Load environment variables
load_dotenv()

# Ensure OpenAI API key and Pinecone API key are set
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET")

# Configure rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "10 per minute"],
    storage_uri="memory://"
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
@limiter.limit("5 per minute")
def analyze():
    try:
        data = request.get_json()
        if not data or 'statement' not in data:
            logger.error("No statement provided in request")
            return jsonify({'error': 'No statement provided'}), 400

        statement = data['statement']
        logger.info(f"Analyzing statement: {statement}")

        # Get API Key securely
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("Missing OPENAI_API_KEY")
            return jsonify({'error': 'API key missing'}), 500

        # Analyze the statement using RAG
        analysis_result = analyze_statement(statement)

        if not analysis_result:
            logger.error("Analysis returned empty result")
            return jsonify({'error': 'Analysis failed to produce results'}), 500

        return jsonify(analysis_result)

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        logger.error(f"Error analyzing statement: {str(e)}")
        return jsonify({'error': 'Analysis failed', 'details': str(e)}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded'}), 429

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500
