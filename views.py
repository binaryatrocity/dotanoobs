import re
from flask import render_template, flash, redirect, g, request, url_for, session
from app import app, db, oid
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
	
	
@app.template_filter('shorten')
def shorten_filter(s, num_words=20):
	space_iter = re.finditer('\s+', s)
	output = u''
	while num_words > 0:
		match = space_iter.next()
		if not match: break
		output = s[:match.end()]
		num_words -= 1
	else:
		output += '...'
	return output
	
### TEMPORARY ###
@app.route('/teamspeak')
def teamspeak():
	return "Teamspeak!"
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
