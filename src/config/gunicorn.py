"""Gunicorn configuration for Gold7 production deployment."""

import multiprocessing

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
worker_tmp_dir = "/dev/shm"  # noqa: S108

# Timeouts
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "gold7"

# Security
limit_request_line = 8190
limit_request_fields = 100
