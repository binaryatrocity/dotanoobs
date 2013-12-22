from flask.ext.sqlalchemy import SQLAlchemy
from app import db

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