import simplejson as json
from datetime import datetime
from random import choice
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.ext.mutable import Mutable

import board
from app import db, app
from utils import parse_valve_heropedia, complete_hero_data, API_DATA

# Model independant get_or_create
def get_or_create_instance(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance

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

# Mongoness factor - phase 2
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
        forum_id = db.Column(db.Integer)
        teamspeak_id = db.Column(db.String(200), unique=True)

	nickname = db.Column(db.String(80))
	avatar = db.Column(db.String(255))
        admin = db.Column(db.Boolean)

        bio_text = db.Column(db.String(4096))
        created = db.Column(db.DateTime)
        last_seen = db.Column(db.DateTime)
        twitch = db.Column(db.String(60))
        random_heroes = db.Column(MutableDict.as_mutable(Json))
        az_completions = db.Column(db.Integer)

        public = db.Column(db.Boolean)
        logo = db.Column(db.Boolean)

        points_from_events = db.Column(db.Integer)
        points_from_ts3 = db.Column(db.Integer)
        points_from_forum = db.Column(db.Integer)
        ts3_starttime = db.Column(db.DateTime)
        ts3_endtime = db.Column(db.DateTime)
        ts3_rewardtime = db.Column(db.DateTime)
        ts3_connections = db.Column(MutableDict.as_mutable(Json))
        last_post_reward = db.Column(db.Integer)


        @classmethod
        def get_or_create(self, steam_id):
            return get_or_create_instance(db.session, User, steam_id=steam_id)

        def __init__(self, steam_id):
            self.steam_id = steam_id
            self.random_heroes = {'current':None, 'completed':[]}
            self.az_completions = 0
            self.created = datetime.utcnow()
            self.last_seen = datetime.utcnow()
            self.bio_text = None 
            self.points_from_events = 0
            self.points_from_ts3 = 0
            self.points_from_forum = 0
            self.admin = False
            self.public = True
            self.biglogo = True
        
        @property
        def random_hero(self):
            if not self.random_heroes['current']:
                heroes = []
                for (tavern_name, tavern) in parse_valve_heropedia():
                    heroes.extend([complete_hero_data('name', entry['name']) for entry in tavern if entry['name'] not in self.random_heroes['completed']])
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
            if len(API_DATA['result']['heroes']) - len(self.random_heroes['completed']) <= 0:
                self.az_completions = self.az_completions + 1
                del self.random_heroes['completed'][:]
            self.random_heroes['current'] = None
            self.random_heroes = self.random_heroes
            db.session.commit()
            return self.random_hero

        def random_skip(self):
            self.random_heroes['current'] = None
            self.random_heroes = self.random_heroes
            db.session.commit()
            return self.random_hero

        def update_connection(self, reward_threshold=30):
            now = datetime.utcnow()
            self.ts3_starttime = self.ts3_starttime or now
            self.ts3_endtime = now
            # Add general TS3 points here
            if self.ts3_endtime and self.ts3_rewardtime:
                duration = (self.ts3_endtime - self.ts3_rewardtime) / 60.0
                if duration > reward_threshold:
                    self.ts3_rewardtime = datetime.utcnow()
                    self.points_from_ts3 += 1
                else:
                    self.ts3_rewardtime = datetime.utcnow()
            self.last_seen = datetime.utcnow()
            print self.ts3_starttime, self.ts3_endtime, self.ts3_rewardtime
            db.session.commit();

        def finalize_connection(self):
            self.ts3_connections.append({'starttime': self.ts3_starttime, 'endtime': self.ts3_endtime})
            self.ts3_startime = None
            self.ts3_endtime = None
            db.session.commit();

        def update_forum_posts(self, reward_threshold=5):
            if self.forum_id:
                posts = board.Users.select().where(board.Users.id == int(self.forum_id))[0].posts
                if self.last_post_reward:
                    num_points = (posts - self.last_post_reward) / reward_threshold
                    if num_points > 0:
                        self.points_from_forum += num_points
                        self.last_post_reward += num_points * reward_threshold
                else:
                    # Initialize if this is the first reward
                    self.last_post_reward = posts
                db.session.commit()

        @property
        def is_active(self):
            return self.ts3_starttime and True or False 

	def __repr__(self):
            return '<User {}>'.format(self.id)

class TeamspeakData(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        time = db.Column(db.DateTime())
        clients = db.Column(Json())

        def __init__(self, clientlist):
            self.time = datetime.utcnow() 
            self.clients = clientlist 

class Event(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(200))
        desc = db.Column(db.String(4096))
        type = db.Column(db.String(20))

        start_time = db.Column(db.DateTime)
        end_time = db.Column(db.DateTime)
        points = db.Column(db.Integer)
        reward_threshold = db.Column(db.Integer)

        total_subchans = db.Column(db.Integer)
        channels = db.Column(MutableDict.as_mutable(Json))
        participants = db.Column(MutableDict.as_mutable(Json))

        def __init__(self, id):
            self.channels = {'event_cid':None, 'cids':[]}

        @classmethod
        def get_or_create(self, event_id):
            return get_or_create_instance(db.session, Event, id=event_id)

        @property
        def cids(self):
            return self.channels['cids']

        @property
        def event_cid(self):
            return self.channels['event_cid']

        @property
        def channel_ids(self):
            cids = self.channels['cids']
            if self.channels['event_cid']:
                cids.append(self.channels['event_cid'])
            return cids

        def create_channels(self):
            import ts3
            server = ts3.TS3Server(app.config['TS3_HOST'], app.config['TS3_PORT'])
            server.login(app.config['TS3_USERNAME'], app.config['TS3_PASSWORD'])
            server.use(1)
            # Create the parent channel
            if not self.event_cid:
                # Find the LFG channel and place this one after
                response = server.send_command('channelfind', keys={'pattern': 'Looking for Group'})
                if response.is_successful:
                    cid = response.data[0]['cid']
                response = server.send_command('channelcreate', keys={'channel_name':self.name.encode('utf-8'), 'channel_flag_semi_permanent':'1', 'channel_order':cid})
                if response.is_successful:
                    self.channels['event_cid'] = response.data[0]['cid']
            # Create the subchannels
            if not self.cids:
                cids = []
                keys = {'channel_name':'Event Room #{}'.format(len(self.cids) + 1), 'channel_flag_semi_permanent':'1', 'cpid':self.event_cid.encode('utf-8')}
                response = server.send_command('channelcreate', keys=keys)
                if response.is_successful:
                    parent_cid = response.data[0]['cid']
                    cids.append(parent_cid)
                else:
                    raise UserWarning("channelcreate failed")
                response = server.send_command('channelcreate', keys={'channel_name':'Radiant Team', 'channel_flag_semi_permanent':'1', 'cpid':parent_cid})
                if response.is_successful:
                    cids.append(response.data[0]['cid'])
                response = server.send_command('channelcreate', keys={'channel_name':'Dire Team', 'channel_flag_semi_permanent':'1', 'cpid':parent_cid})
                if response.is_successful:
                    cids.append(response.data[0]['cid'])
                response = server.send_command('channelcreate', keys={'channel_name':'Spectators', 'channel_flag_semi_permanent':'1', 'cpid':parent_cid})
                if response.is_successful:
                    cids.append(response.data[0]['cid'])
                self.channels['cids'] = cids
            db.session.commit()
        
        def remove_channels(self):
            import ts3
            server = ts3.TS3Server(app.config['TS3_HOST'], app.config['TS3_PORT'])
            server.login(app.config['TS3_USERNAME'], app.config['TS3_PASSWORD'])
            server.use(1)
            response = server.send_command('channeldelete', keys={'cid':self.event_cid.encode('utf-8'), 'force':'1'})
            if response.is_successful:
                self.channels = {'event_cid': None, 'cids':[]}
                db.session.commit()

        @property
        def active(self):
            current_time = datetime.utcnow()
            return self.start_time < current_time and current_time < self.end_time

        @property
        def expired(self):
            current_time = datetime.utcnow()
            return self.end_time < curent_time

        def add_participant(self, user):
            entry = self.participants.setdefault(user, {'start_time': datetime.utcnow() })
            entry['end_time'] = datetime.utcnow()
            if 'points' not in entry and (entry['end_time'] - entry['start_time']) > self.reward_threshold:
                user.points_from_events += self.points
                entry['points'] = self.points
            db.session.commit()

        @property
        def participants(self):
            return tuple(self.participants)

        def __repr__(self):
            return '<Event {}>'.format(self.id)
