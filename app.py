import os
import logging
from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, PoliticalStatement
from rag_engine import analyze_statement

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///politics.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Configure rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "10 per minute"],
    storage_uri="memory://"
)

# Create database tables
with app.app_context():
    db.create_all()

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

        # Analyze the statement using RAG
        analysis_result = analyze_statement(statement)

        if not analysis_result:
            logger.error("Analysis returned empty result")
            return jsonify({'error': 'Analysis failed to produce results'}), 500

        # Store the statement and analysis in the database
        try:
            new_statement = PoliticalStatement(
                statement=statement,
                analysis_result=analysis_result
            )
            db.session.add(new_statement)
            db.session.commit()
            logger.info("Statement and analysis saved to database")
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            # Continue even if database save fails
            pass

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