from flask import Flask
from flask_bootstrap import Bootstrap
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import os

app=Flask(__name__)
bootstrap = Bootstrap(app)
app.config.from_object(Config)


file_handler = RotatingFileHandler('/tmp/ottstreamer.log', 
    maxBytes=10240,backupCount=10)
file_handler.setFormatter(logging.Formatter(
     '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)
app.logger.info('Ottstreamer startup')

from redis import Redis
from rq import Queue,Worker
app.redis=Redis('localhost',6379)
app.cache_queue=Queue("cache-commercials",connection=app.redis,default_timeout=600)
app.encode_queue=Queue("encode-commercials",connection=app.redis,default_timeout=7200)


from app import routes
