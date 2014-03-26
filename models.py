import simplejson as json
from random import choice
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import Mutable
from time import time
from app import db
from utils import parse_valve_heropedia, complete_hero_data

# Get a little of that Mongoness back
class Json(db.TypeDecorator):
    impl = db.Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)
            return Mutable.coerce(key,value)
        else:
            return value

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(self)



class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	steam_id = db.Column(db.String(40), unique=True)
	nickname = db.Column(db.String(80))
	avatar = db.Column(db.String(255))
        random_heroes = db.Column(MutableDict.as_mutable(Json))
        bio_text = db.Column(db.String(4096))
        last_seen = db.Column(db.DateTime)
        twitch = db.Column(db.String(60))
	
	@staticmethod
	def get_or_create(steam_id):
            rv = User.query.filter_by(steam_id=steam_id).first()
            if rv is None:
                rv = User()
                rv.steam_id = steam_id
                rv.random_heroes = {'current':None, 'completed':[]}
                bio_text = ''
                db.session.add(rv)
            return rv
        
        @property
        def random_hero(self):
            if not self.random_heroes['current']:
                heroes = []
                for (tavern_name, tavern) in parse_valve_heropedia():
                    heroes.extend([complete_hero_data('name', entry['name']) for entry in tavern])
                if heroes:
                    self.random_heroes['current'] = choice(heroes)
                    self.random_heroes = self.random_heroes
                    db.session.commit()
            return self.random_heroes['current']

        @random_hero.setter
        def random_hero(self, herodata):
            self.random_heroes['current'] = herodata
            self.random_heroes = self.random_heroes
            db.session.commit()

        @property
        def random_completed(self):
            return self.random_heroes['completed']

        def random_success(self):
            self.random_heroes['completed'].append(self.random_heroes['current']['name'])
            self.random_heroes['current'] = None
            self.random_heroes = self.random_heroes
            db.session.commit()
            return self.random_hero

        def random_skip(self):
            self.random_heroes['current'] = None
            self.random_heroes = self.random_heroes
            db.session.commit()
            return self.random_hero

	def __repr__(self):
            return '<User {}>'.format(self.nickname)

class TeamspeakData(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        time = db.Column(db.Float())
        clients = db.Column(Json())

        def __init__(self, clientlist):
            self.time = time()
            self.clients = clientlist 
