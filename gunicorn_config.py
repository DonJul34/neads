bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
timeout = 120
pythonpath = "/var/www/neads/app/neads"
user = "www-data"
group = "www-data"
errorlog = "/var/www/neads/app/neads/logs/gunicorn-error.log"
accesslog = "/var/www/neads/app/neads/logs/gunicorn-access.log" 