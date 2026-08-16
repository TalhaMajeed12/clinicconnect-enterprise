bind = "0.0.0.0:8000"
# Filesystem sessions are process-local. Keep one worker until REDIS_URL is set.
workers = 1
worker_class = "sync"
timeout = 30
accesslog = "-"
errorlog = "-" 
