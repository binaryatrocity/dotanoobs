from flask import render_template, flash, redirect, g, request, url_for, session

from datetime import datetime
from functools import wraps

from app import app, db, oid
from models import User, Event
from utils import get_steam_userinfo
from board import registerUserForumId
from teamspeak import registerUserTeamspeakId
from forms import SettingsForm, EventForm, EnableStatsForm

@app.before_request
def before_request():
	g.user = None
	if 'user_id' in session:
            g.user = User.query.get(session['user_id'])
            if g.user:
                g.user.last_seen = datetime.utcnow()
                db.session.commit()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def flash_form_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(u"Error in the %s field - %s" % (getattr(form,field).label.text, error), 'danger')

#
# Application routes
#

@app.route('/')
def index():
    active = Event.query.filter(Event.start_time <= datetime.utcnow(), Event.end_time > datetime.utcnow()).all()
    upcoming =  Event.query.filter(Event.start_time > datetime.utcnow()).limit(2).all()
    channels = User.get_streaming_users()
    return render_template("index.html", active_events=active, upcoming_events=upcoming, streamers=channels)
	
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
        flash("You are logged in as {}".format(g.user.nickname), 'success')
	return redirect(oid.get_next_url())

@app.route('/logout')
def logout():
	session.pop('user_id', None)
        g.user = None
        flash("You have been logged out.", 'success')
	return redirect(url_for('index'))
	
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
@login_required
def user_settings():
    user = User.query.filter_by(id=g.user.id).first_or_404()
    form = SettingsForm(obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        if user.bio_text == '':
            user.bio_text = None
        db.session.commit()
        flash('Settings updated!', 'success')
    return render_template('settings.html', form=form)

# Enable user statistics page
@app.route('/settings/enable_stats', methods=['POST', 'GET'])
@login_required
def enable_statistics():
    # TODO: update user_settings to use g.user, avoid extra queries
    form = EnableStatsForm(obj=g.user)
    if form.validate_on_submit():
        forum_data = registerUserForumId(g.user, form.forum_username.data, form.forum_password.data)
        if forum_data:
            flash('Forum account \''+forum_data['forum_name']+'\' linked!', 'success')
        else:
            flash('Forum account credentials invalid', 'danger')
        if registerUserTeamspeakId(g.user, form.teamspeak_id.data):
            flash('Teamspeak account linked successfully!', 'success')
        else:
            flash('Teamspeak ID not found in client history', 'danger')
    return render_template('enable_stats.html', form=form)

# Events list
@app.route('/events', methods=['GET'])
def list_events():
    now = datetime.utcnow()
    active = Event.query.filter(Event.start_time <= now, Event.end_time > now).all()
    upcoming = Event.query.filter(Event.start_time > now).all()
    expired = Event.query.filter(Event.end_time < now).all()
    return render_template('list_events.html', active=active, upcoming=upcoming, expired=expired)

# Show event info
@app.route('/event/<int:eventid>', methods=['GET'])
def show_event(eventid):
    event = Event.query.filter_by(id=eventid).first_or_404()
    return render_template('show_event.html', event=event)

# Event creation page
@app.route('/event/edit', methods=['POST', 'GET'])
@login_required
def event_edit():
    if not g.user.admin:
        flash('Access Denied: You cannot create/edit events.', 'danger')
        return redirect(url_for('index'))
    eventid = request.args.get('eventid')
    event = Event.get_or_create(eventid)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        form.populate_obj(event)
        db.session.add(event)
        db.session.commit()
        flash('New event created!', 'success') if eventid is None else flash('Event updated successfully!', 'success')
        return redirect(url_for('show_event', eventid=event.id))
    else:
        flash_form_errors(form)
    return render_template('edit_event.html', event=event, form=form)

# Event deletion call
@app.route('/event/<int:eventid>/delete', methods=['GET'])
@login_required
def event_delete(eventid):
    if g.user.admin:
        event = Event.query.filter_by(id=eventid).first_or_404()
        flash('Info: Event "{}" deleted successfully.'.format(event.name), 'success')
        db.session.delete(event)
        db.session.commit()
    else:
        flash('Access Denied: You cannot delete events.', 'danger')
    return redirect(url_for('index'))
