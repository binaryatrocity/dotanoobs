import simplejson as json
from flask.ext.sqlalchemy import SQLAlchemy
from time import time
from app import db

# Get a little of that Mongoness back
class Json(db.TypeDecorator):
        impl = db.Unicode

        def process_bind_param(self, value, dialect):
            return unicode(json.dumps(value))

        def process_result_value(self, value, dialect):
            return json.loads(value)

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	steam_id = db.Column(db.String(40), unique=True)
	nickname = db.Column(db.String(80))
	avatar = db.Column(db.String(255))
	
	@staticmethod
	def get_or_create(steam_id):
		rv = User.query.filter_by(steam_id=steam_id).first()
		if rv is None:
			rv = User()
			rv.steam_id = steam_id
			db.session.add(rv)
		return rv

	def __repr__(self):
		return '<User {}>'.format(self.steam_id)

class TeamspeakData(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        time = db.Column(db.Float())
        clients = db.Column(Json())

        def __init__(self, clientlist):
            self.time = time()
            self.clients = clientlist 
