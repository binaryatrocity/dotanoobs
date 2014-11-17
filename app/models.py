import simplejson as json
from datetime import datetime, timedelta
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
        try:
            if value is not None:
                value = json.loads(value)
        except ValueError:
            return {}
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

        bio_text = db.Column(db.String(4096))
        created = db.Column(db.DateTime)
        last_seen = db.Column(db.DateTime)
        twitch = db.Column(db.String(60))
        hitbox = db.Column(db.String(60))

        admin = db.Column(db.Boolean)
        public = db.Column(db.Boolean)
        logo = db.Column(db.Boolean)

        points_from_events = db.Column(db.Integer)
        points_from_ts3 = db.Column(db.Integer)
        points_from_forum = db.Column(db.Integer)

        ts3_starttime = db.Column(db.DateTime)
        ts3_endtime = db.Column(db.DateTime)
        ts3_rewardtime = db.Column(db.DateTime)
        ts3_stretch_award_time = db.Column(db.DateTime)
        ts3_longest_stretch = db.Column(db.Interval)

        last_post_reward = db.Column(db.Integer)
        winrate_data = db.Column(MutableDict.as_mutable(Json))


        @classmethod
        def get_or_create(self, steam_id):
            return get_or_create_instance(db.session, User, steam_id=steam_id)

        @classmethod
        def get_streaming_users(self):
            twitch_streams = []
            hitbox_streams = []
            for user in User.query.all():
		if user.points_from_events + user.points_from_ts3 + user.points_from_forum < 5: continue
                if user.twitch:
                    twitch_streams.append(user.twitch)
                if user.hitbox:
                    hitbox_streams.append(user.hitbox)

            return {'twitch': twitch_streams, 'hitbox': hitbox_streams}

        def __init__(self, steam_id):
            self.steam_id = steam_id
            self.az_completions = 0
            self.ts3_rewardtime = datetime.utcnow()
            self.ts3_longest_stretch = timedelta()
            self.created = datetime.utcnow()
            self.last_seen = datetime.utcnow()
            self.bio_text = None 
            self.points_from_events = 0
            self.points_from_ts3 = 0
            self.points_from_forum = 0
            self.admin = False
            self.public = True
            self.biglogo = True

        def update_connection(self, reward_threshold=30):
            now = datetime.utcnow()
            self.ts3_starttime = self.ts3_starttime or now
            self.ts3_endtime = now

            # Add general TS3 points here
            delta = (self.ts3_endtime - self.ts3_rewardtime)
            duration = (delta.seconds % 3600) // 60
            if duration > reward_threshold:
                self.ts3_rewardtime = datetime.utcnow()
                self.points_from_ts3 += 1

            # Update last_seen for web profile
            self.last_seen = datetime.utcnow()
            db.session.commit();

        def finalize_connection(self):
            # Check for longest!
            if self.ts3_endtime and self.ts3_starttime:
                current_stretch = self.ts3_endtime - self.ts3_starttime
                if current_stretch > self.ts3_longest_stretch:
                    self.ts3_longest_stretch = current_stretch
                    self.ts3_stretch_award_time = datetime.utcnow()

            # Reset values
            self.ts3_starttime = None
            self.ts3_endtime = None
            db.session.commit();

        def update_forum_posts(self, reward_threshold=5):
            if self.forum_id:
                posts = board.Users.select().where(board.Users.id == int(self.forum_id))[0].posts
                if self.last_post_reward:
                    num_points = (posts - self.last_post_reward) / reward_threshold
                    print("Old: {0}, New: {1}, ({0} - {1}) / {2}, {3}, {4}".format(self.last_post_reward, posts, reward_threshold, num_points, self.nickname))
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
            return self.end_time < current_time

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
