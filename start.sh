#!/bin/bash


# Download NLTK data
python post_install.py

# Start the web server with Gunicorn
gunicorn app:app