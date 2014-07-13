from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.openid import OpenID
from flask.ext.cache import Cache

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)
oid = OpenID(app)
cache = Cache(app, config={'CACHE_TYPE': app.config['CACHE_TYPE']})

from app import views
