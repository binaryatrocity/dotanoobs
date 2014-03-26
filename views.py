from flask import render_template, flash, redirect, g, request, url_for, session
from datetime import datetime

from app import app, db, oid, cache
from models import User
from utils import get_steam_userinfo
from board import latest_news
from forms import SettingsForm

@app.before_request
def before_request():
	g.user = None
	if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
            if g.user:
                g.user.last_seen = datetime.utcnow()
                db.session.commit()

@app.route('/')
def index():
	return render_template("index.html", latest_news=latest_news())
	
@app.route('/login')
@oid.loginhandler
def login():
	if g.user is not None:
		return redirect(oid.get_next_url())
	return oid.try_login('http://steamcommunity.com/openid')
	
@oid.after_login
def create_or_login(resp):
	match = app.config['STEAM_ID_RE'].search(resp.identity_url)
	g.user = User.get_or_create(match.group(1))
	steamdata = get_steam_userinfo(g.user.steam_id)
	g.user.nickname = steamdata['personaname']
	g.user.avatar = steamdata['avatar']
	db.session.commit()
	session['user_id'] = g.user.id
        flash("You are logged in as {}".format(g.user.nickname))
	return redirect(oid.get_next_url())

@app.route('/logout')
def logout():
	session.pop('user_id', None)
	return redirect(oid.get_next_url())
	

### TEMPORARY ###
@app.route('/list_events')
def list_events():
	return "Events list!"
@app.route('/community')
def community():
	return "Community!"
@app.route('/ladder')
def ladder():
	return "Ladder!"
### ###


# Teamspeak statistics page
@app.route('/teamspeak')
def teamspeak():
        return render_template('teamspeak.html')

# Friends of doobs page
@app.route('/friends')
def friends():
	return render_template('friends.html') 

# User profile page
@app.route('/user/<int:userid>')
def user_profile(userid):
    user = User.query.filter_by(id=userid).first_or_404()
    return render_template('profile.html', user=user)

# User random a-z challenge progress page
@app.route('/user/<int:userid>/random', methods=['POST', 'GET'])
def user_random_hero(userid):
    user = User.query.filter_by(id=userid).first_or_404()
    if request.method == 'POST':
        if request.form.get('skip', False):
            user.random_skip()
        elif request.form.get('completed', False):
            user.random_success()
    return render_template('hero_random.html', user=user)

# User settings page
@app.route('/settings', methods=['POST', 'GET'])
def user_settings():
    user = User.query.filter_by(id=g.user.id).first_or_404()
    form = SettingsForm(obj=user)
    if form.validate_on_submit():
        g.user.bio_text = form.bio_text.data
        g.user.twitch = form.twitch.data
        db.session.commit()
        flash('Settings updated!')
        return render_template('profile.html', user=g.user)
    else:
        form.populate_obj(user)
    return render_template('settings.html', user=g.user, form=form)
