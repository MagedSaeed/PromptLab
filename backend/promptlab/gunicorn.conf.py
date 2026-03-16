# gunicorn_config.py

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = 4
threads = 4

# Logging
errorlog = "/var/log/gunicorn/error.log"
loglevel = "debug"
accesslog = "/var/log/gunicorn/access.log"
