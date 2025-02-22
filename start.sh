#!/bin/bash


# Download NLTK data
python post_install.py

# Set NLTK data environment variable
export NLTK_DATA=/opt/render/nltk_data

# Start the web server with Gunicorn
gunicorn app:app