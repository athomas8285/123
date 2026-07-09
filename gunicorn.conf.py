"""Production config"""
import os

wsgi_app = "dashboard:app"
bind = f"0.0.0.0:{os.environ.get('PORT', '5021')}"
workers = 2
loglevel = "debug"
accesslog = "-"
capture_output = True
preload_app = True
timeout = 120
