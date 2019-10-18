#! /usr/bin/python3

import logging
import sys
import os
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/ddrive/ottstreamer/webapp')
from app import app as application
application.secret_key = 'somekey'

