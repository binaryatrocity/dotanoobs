import os
import re
from time import strftime, gmtime
from hashlib import sha256
from peewee import *

from app import app, cache, db

board_db = MySQLDatabase(app.config['FORUM_NAME'], **{'passwd': app.config['FORUM_PASSWORD'],
					'host': app.config['FORUM_HOST'], 'user': app.config['FORUM_USERNAME']})

def registerUserForumId(user, username, password):
    try:
        u = Users.filter(name=username).get()
        hashpass = sha256(password+app.config['FORUM_SALT']+u.pss).hexdigest()
        if hashpass == u.password:
            user.forum_id = u.id
            db.session.commit()
            return {"forum_name":u.name, "forum_id":u.id}
    except DoesNotExist:
        pass
    return False

@cache.memoize(60*5)
def latest_news(num=3):
	latest_news = []
        try:
		board_db.connect()
		news_forum = Forums.get(fn.Lower(Forums.title) % '%news%')
		for thread in Threads.select().where(
			Threads.forum == news_forum.id).order_by(Threads.date.desc()).limit(num):
				# Last revision of the first post
				post = Posts.select().where(Posts.thread == thread.id).get()
				raw_text = PostsText.select().where(PostsText.pid == post.id).order_by(PostsText.revision.desc()).limit(1).get()

                                #remove BBCode
                                text = re.sub(r"\[(\/)?(\w+)\]", '', raw_text.text)

				timestamp = thread.date
				date = strftime('%B %d, %Y %H:%M:%S UTC', gmtime(timestamp))
				if not timestamp:
					post = Posts.select().where(Posts.thread == thread.id).get()
					timestamp = post and post.date
				url = 'http://board.dotanoobs.com/?page=thread&id=%d' % thread.id
				latest_news.append({'title':thread.title, 'text':text, 'date':date, 'timestamp':timestamp, 'url':url})
	except Exception as e:
		latest_news.append({'title':'Error with forum db', 'text':e, 'url':''})
        finally:
		board_db.close()
	return latest_news
					
class UnknownFieldType(object):
    pass

class BaseModel(Model):
    class Meta:
        database = board_db

class Badges(BaseModel):
    color = IntegerField()
    name = CharField()
    owner = IntegerField()

    class Meta:
        db_table = 'badges'

class Blockedlayouts(BaseModel):
    blockee = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'blockedlayouts'

class Categories(BaseModel):
    corder = IntegerField()
    name = CharField()

    class Meta:
        db_table = 'categories'

class Enabledplugins(BaseModel):
    plugin = CharField()

    class Meta:
        db_table = 'enabledplugins'

class Forummods(BaseModel):
    forum = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'forummods'

class Forums(BaseModel):
    catid = IntegerField()
    description = TextField(null=True)
    forder = IntegerField()
    hidden = IntegerField()
    lastpostdate = IntegerField()
    lastpostid = IntegerField()
    lastpostuser = IntegerField()
    minpower = IntegerField()
    minpowerreply = IntegerField()
    minpowerthread = IntegerField()
    numposts = IntegerField()
    numthreads = IntegerField()
    title = CharField()

    class Meta:
        db_table = 'forums'

class Guests(BaseModel):
    bot = IntegerField()
    date = IntegerField()
    ip = CharField()
    lastforum = IntegerField()
    lasturl = CharField()
    useragent = CharField()

    class Meta:
        db_table = 'guests'

class Ignoredforums(BaseModel):
    fid = IntegerField()
    uid = IntegerField()

    class Meta:
        db_table = 'ignoredforums'

class Ip2C(BaseModel):
    cc = CharField(null=True)
    ip_from = BigIntegerField()
    ip_to = BigIntegerField()

    class Meta:
        db_table = 'ip2c'

class Ipbans(BaseModel):
    date = IntegerField()
    ip = CharField()
    reason = CharField()

    class Meta:
        db_table = 'ipbans'

class Log(BaseModel):
    date = IntegerField()
    forum = IntegerField()
    forum2 = IntegerField()
    ip = CharField()
    pm = IntegerField()
    post = IntegerField()
    text = CharField()
    thread = IntegerField()
    type = CharField()
    user = IntegerField()
    user2 = IntegerField()

    class Meta:
        db_table = 'log'

class Misc(BaseModel):
    hotcount = IntegerField()
    maxpostsday = IntegerField()
    maxpostsdaydate = IntegerField()
    maxpostshour = IntegerField()
    maxpostshourdate = IntegerField()
    maxusers = IntegerField()
    maxusersdate = IntegerField()
    maxuserstext = TextField(null=True)
    milestone = TextField(null=True)
    version = IntegerField()
    views = IntegerField()

    class Meta:
        db_table = 'misc'

class Moodavatars(BaseModel):
    mid = IntegerField()
    name = CharField()
    uid = IntegerField()

    class Meta:
        db_table = 'moodavatars'

class Notifications(BaseModel):
    description = TextField(null=True)
    link = IntegerField()
    linklocation = CharField()
    time = IntegerField()
    title = CharField()
    type = CharField()
    uid = IntegerField()

    class Meta:
        db_table = 'notifications'

class Pmsgs(BaseModel):
    date = IntegerField()
    deleted = IntegerField()
    drafting = IntegerField()
    ip = CharField()
    msgread = IntegerField()
    userfrom = IntegerField()
    userto = IntegerField()

    class Meta:
        db_table = 'pmsgs'

class PmsgsText(BaseModel):
    pid = IntegerField()
    text = TextField(null=True)
    title = CharField()

    class Meta:
        db_table = 'pmsgs_text'

class Poll(BaseModel):
    briefing = TextField(null=True)
    closed = IntegerField()
    doublevote = IntegerField()
    question = CharField()

    class Meta:
        db_table = 'poll'

class PollChoices(BaseModel):
    choice = CharField()
    color = CharField()
    poll = IntegerField()

    class Meta:
        db_table = 'poll_choices'

class Pollvotes(BaseModel):
    choiceid = IntegerField()
    poll = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'pollvotes'

class Postplusones(BaseModel):
    post = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'postplusones'

class Posts(BaseModel):
    currentrevision = IntegerField()
    date = IntegerField()
    deleted = IntegerField()
    deletedby = IntegerField()
    ip = CharField()
    mood = IntegerField()
    num = IntegerField()
    options = IntegerField()
    postplusones = IntegerField()
    reason = CharField()
    thread = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'posts'

class PostsText(BaseModel):
    date = IntegerField()
    pid = IntegerField(primary_key=True)
    revision = IntegerField()
    text = TextField(null=True)
    user = IntegerField()

    class Meta:
        db_table = 'posts_text'

class Proxybans(BaseModel):
    ip = CharField()

    class Meta:
        db_table = 'proxybans'

class Queryerrors(BaseModel):
    cookie = TextField(null=True)
    error = TextField(null=True)
    get = TextField(null=True)
    ip = CharField()
    post = TextField(null=True)
    query = TextField(null=True)
    time = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'queryerrors'

class Reports(BaseModel):
    hidden = IntegerField()
    ip = CharField()
    request = TextField(null=True)
    severity = IntegerField()
    text = CharField()
    time = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'reports'

class Sessions(BaseModel):
    autoexpire = IntegerField()
    expiration = IntegerField()
    id = CharField()
    iplock = IntegerField()
    iplockaddr = CharField()
    lastip = CharField()
    lasttime = IntegerField()
    lasturl = CharField()
    user = IntegerField()

    class Meta:
        db_table = 'sessions'

class Settings(BaseModel):
    name = CharField()
    plugin = CharField()
    value = TextField(null=True)

    class Meta:
        db_table = 'settings'

class Smilies(BaseModel):
    code = CharField()
    image = CharField()

    class Meta:
        db_table = 'smilies'

class Threads(BaseModel):
    closed = IntegerField()
    date = IntegerField()
    firstpostid = IntegerField()
    forum = IntegerField()
    icon = CharField()
    lastpostdate = IntegerField()
    lastposter = IntegerField()
    lastpostid = IntegerField()
    poll = IntegerField()
    replies = IntegerField()
    sticky = IntegerField()
    title = CharField()
    user = IntegerField()
    views = IntegerField()

    class Meta:
        db_table = 'threads'

class Threadsread(BaseModel):
    date = IntegerField()
    thread = IntegerField()

    class Meta:
        db_table = 'threadsread'

class Uploader(BaseModel):
    category = IntegerField()
    date = IntegerField()
    description = CharField()
    downloads = IntegerField()
    filename = CharField()
    private = IntegerField()
    user = IntegerField()

    class Meta:
        db_table = 'uploader'

class UploaderCategories(BaseModel):
    description = TextField(null=True)
    name = CharField()
    ord = IntegerField()

    class Meta:
        db_table = 'uploader_categories'

class Usercomments(BaseModel):
    cid = IntegerField()
    date = IntegerField()
    text = TextField(null=True)
    uid = IntegerField()

    class Meta:
        db_table = 'usercomments'

class Usergroups(BaseModel):
    inherits = IntegerField()
    permissions = TextField(null=True)
    title = CharField()

    class Meta:
        db_table = 'usergroups'

class Userpermissions(BaseModel):
    permissions = TextField(null=True)
    uid = IntegerField()

    class Meta:
        db_table = 'userpermissions'

class Users(BaseModel):
    bio = TextField(null=True)
    birthday = IntegerField()
    blocklayouts = IntegerField()
    color = CharField()
    dateformat = CharField()
    displayname = CharField()
    email = CharField()
    fontsize = IntegerField()
    forbiddens = CharField()
    globalblock = IntegerField()
    hascolor = IntegerField()
    homepagename = CharField()
    homepageurl = CharField()
    karma = IntegerField()
    lastactivity = IntegerField()
    lastforum = IntegerField()
    lastip = CharField()
    lastknownbrowser = TextField(null=True)
    lastposttime = IntegerField()
    lasturl = CharField()
    location = CharField()
    loggedin = IntegerField()
    lostkey = CharField()
    lostkeytimer = IntegerField()
    minipic = CharField()
    name = CharField()
    newcomments = IntegerField()
    password = CharField()
    picture = CharField()
    pluginsettings = TextField(null=True)
    postheader = TextField(null=True)
    postplusones = IntegerField()
    postplusonesgiven = IntegerField()
    posts = IntegerField()
    postsperpage = IntegerField()
    powerlevel = IntegerField()
    pss = CharField()
    rankset = CharField()
    realname = CharField()
    regdate = IntegerField()
    sex = IntegerField()
    showemail = IntegerField()
    signature = TextField(null=True)
    signsep = IntegerField()
    tempbanpl = IntegerField()
    tempbantime = BigIntegerField()
    theme = CharField()
    threadsperpage = IntegerField()
    timeformat = CharField()
    timezone = FloatField()
    title = CharField()
    usebanners = IntegerField()

    class Meta:
        db_table = 'users'

class Uservotes(BaseModel):
    uid = IntegerField()
    up = IntegerField()
    voter = IntegerField()

    class Meta:
        db_table = 'uservotes'

class WikiPages(BaseModel):
    flags = IntegerField()
    id = CharField()
    revision = IntegerField()

    class Meta:
        db_table = 'wiki_pages'

class WikiPagesText(BaseModel):
    date = IntegerField()
    id = CharField()
    revision = IntegerField()
    text = TextField(null=True)
    user = IntegerField()

    class Meta:
        db_table = 'wiki_pages_text'
