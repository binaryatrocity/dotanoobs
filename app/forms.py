from flask_wtf import Form
from wtforms import TextField, BooleanField, TextAreaField, PasswordField, SelectField, IntegerField, DateTimeField, validators
from datetime import datetime

class SettingsForm(Form):
    public = BooleanField('public', default=True)
    logo = BooleanField('biglogo', default=True)
    twitch = TextField('twitch')
    hitbox = TextField('hitbox')
    bio_text = TextAreaField('bio_text')

class EnableStatsForm(Form):
    teamspeak_id = TextField('teamspeak_id')
    forum_username = TextField('forum_username')
    forum_password = PasswordField('forum_password')

class EventForm(Form):
    name = TextField('name', [validators.Required()])
    desc = TextAreaField('desc', [validators.Required()])
    type = SelectField(u'Event Type', choices=[('coaching', 'Coaching'), ('inhouse', 'In-House'), ('tournament', 'Tournament'), ('other', 'Other')])
    start_time = DateTimeField('start_time', format='%d.%m.%Y %H:%M')
    end_time = DateTimeField('end_time', format='%d.%m.%Y %H:%M')
    points = IntegerField('points', [validators.Required()])
    reward_threshold = IntegerField('reward_threshold')
