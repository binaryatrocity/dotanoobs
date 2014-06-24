from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.openid import OpenID
from flask.ext.cache import Cache

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)
oid = OpenID(app)
cache = Cache(app, config={'CACHE_TYPE': app.config['CACHE_TYPE']})

import ts3
from apscheduler.schedulers.background import BackgroundScheduler
from teamspeak import idle_mover, store_active_data, \
        process_ts3_events, award_idle_ts3_points

def set_voice_server():
    ts3Server = ts3.TS3Server(app.config['TS3_HOST'], app.config['TS3_PORT'])
    ts3Server.login(app.config['TS3_USERNAME'], app.config['TS3_PASSWORD'])
    ts3Server.use(1)
    return ts3Server

voice = set_voice_server()

def refresh_voice_server():
    app.logger.info("Refreshing TS3 connection...")
    voice = set_voice_server()

scheduler = BackgroundScheduler(logger=app.logger)
scheduler.add_job(refresh_voice_server, 'interval', hours=6)
scheduler.add_job(idle_mover, 'interval', [voice],  minutes=30)
scheduler.add_job(store_active_data, 'interval', [voice],  minutes=30)
scheduler.add_job(award_idle_ts3_points, 'interval', [voice],  minutes=30)
scheduler.add_job(process_ts3_events, 'interval', [voice],  hours=1)
scheduler.start()

from app import views, models
