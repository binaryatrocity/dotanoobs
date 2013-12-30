from flask import render_template, flash, redirect, g, request, url_for, session

from app import app, db, oid, cache
from models import User
from utils import get_steam_userinfo
from board import latest_news

@app.before_request
def before_request():
	g.user = None
	if 'user_id' in session:
		g.user = User.query.get(session['user_id'])

@app.route('/')
@app.route('/main')
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
@app.route('/teamspeak')
def teamspeak():
        return render_template('teamspeak.html')
@app.route('/list_events')
def list_events():
	return "Events list!"
@app.route('/friends')
def friends():
	return render_template('friends.html') 
@app.route('/community')
def community():
	return "Community!"
@app.route('/ladder')
def ladder():
	return "Ladder!"

#From league/doobs_blueprint.py
@app.route('/profile/<int:userid>')
def user_profile(userid):
    user = User.query.filter_by(id=userid).first_or_404()
    return render_template('profile.html', user=user)

'''
from flask import render_template, flash, redirect, g, request, url_for
from app import app, oid

@app.route('/login')
@oid.loginhandler
def login():
	if g.user is not None:
		return redirect(oid.get_next_url())
	return oid.try_login('http://www.steamcommunity.com/openid')
	
@oid.after_login
def check_login(resp):
	match = app.config['STEAM_ID_RE'].search(resp.identity_url)
	return "none"
	
@app.route('/')
def main():
	return render_template('main.html')

@app.route('/community')
def community():
	return render_template('community.html', latest_posts=latest_posts())

@app.route('/friends')
def friends():
	return render_template('friends.html')

@app.route('/teamspeak')
def teamspeak():
	return render_template('teamspeak.html')
	
@app.route('/events')
def list_events():
	return render_template('events.html')
	
@app.route('/events/<int:id>')
def event_summary(id):
	return render_template('events.html')
	
@app.route('/ladder')
def ladder():
	return render_template('ladder.html')
	'''
