#!/bin/bash
# Render start command
pip install gunicorn && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
