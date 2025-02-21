#!/bin/bash
# Run the document ingester to initialize the vector store

python document_ingester.py

# Start the web server with Gunicorn
gunicorn app:app