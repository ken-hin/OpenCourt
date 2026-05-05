# Procfile — Tells Railway (and Render, Heroku, etc.) how to run the app.
#
# "web" is the process that serves HTTP requests.
# Gunicorn is a production-grade WSGI server — it replaces `python manage.py runserver`.
#
# Flags:
#   --bind 0.0.0.0:$PORT   → Listen on the port Railway assigns (via $PORT env var)
#   --workers 2             → Run 2 worker processes to handle concurrent requests
#                              (Railway free tier has limited RAM, so 2 is plenty)

web: gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --timeout 120
