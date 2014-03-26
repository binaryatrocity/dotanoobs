from flask.ext.wtf import Form
from wtforms import TextField, BooleanField, TextAreaField

class SettingsForm(Form):
    public = BooleanField('public', default=True)
    twitch = TextField('twitch')
    bio_text = TextAreaField('bio_text')
