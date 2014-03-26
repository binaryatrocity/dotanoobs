from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.openid import OpenID
from flask.ext.cache import Cache

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
oid = OpenID(app)
cache = Cache(app, config={'CACHE_TYPE': app.config['CACHE_TYPE']})

from app import views

'''
from flask import Flask, render_template
from flask.ext.mongoengine import MongoEngine
from flask.ext.openid import OpenID
from flask.ext.cache import Cache
import utils
import ts3

app = Flask(__name__)
app.config.from_object('config')

#Setup mongo database
db = MongoEngine(app)

#Setup OpenID and Caching
oid = OpenID(app)
cache = Cache(app, config={'CACHE_TYPE': app.config['CACHE_TYPE']})

from app import views
@app.route('/')
def inx():
	return render_template('main.html')
	
##### INTO UTILS LATER #####
RADIANT_TEAM = 2
DIRE_TEAM = 3
RADIANT_COLOR = 'b'
DIRE_COLOR = 'r'

def get_hero_data():
	xhr = urllib2.build_opener().open(urllib2.Request("https://api.steampowered.com/IEconDOTA2_570/GETHeroes/v0001/?key="+DOTA2_API_KEY+"&language=en_us"))
	data = json.load(xhr)
	return data
	
@app.context_processor
def utility_processor():
	@cache.memoize(60*5)
	def ts3_viewer():
		try:
			server = ts3.TS3Server(app.config['TS3_HOST'], app.config['TS3_PORT'])
			server.login(app.config['TS3_USERNAME'], app.config['TS3_PASSWORD'])
			server.use(1)

			serverinfo = server.send_command('serverinfo').data
			channellist = server.send_command('channellist', opts=("limits", "flags", "voice", "icon")).data
			clientlist = server.send_command('clientlist', opts=("away", "voice", "info", "icon", "groups", "country")).data
			servergrouplist = server.send_command('servergrouplist').data
			channelgrouplist = server.send_command('channelgrouplist').data

			soup = BeautifulSoup()
			div_tag = soup.new_tag('div')
			div_tag['class'] ='devmx-webviewer'
			soup.append(div_tag)

			def construct_channels(parent_tag, cid):
				num_clients = 0
				for channel in channellist:
					if int(channel['pid']) == int(cid):
						# Construct the channel
						channel_tag = soup.new_tag('div')
						channel_tag['class'] = 'tswv-channel'
						# Channel image
						image_tag = soup.new_tag('span')
						image_tag['class'] = 'tswv-image tswv-image-right'
						if int(channel['channel_flag_password']) == 1:
							image_tag['class'] += ' tswv-channel-password-right'
						if int(channel['channel_flag_default']) == 1:
							image_tag['class'] += ' tswv-channel-home'
						if int(channel['channel_needed_talk_power']) > 0:
							image_tag['class'] += ' tswv-channel-moderated'
						if int(channel['channel_icon_id']) != 0:
							raise NotImplementedError
						image_tag.append('&nbsp;')
						channel_tag.append(image_tag)
						# Status image
						status_tag = soup.new_tag('span')
						status_tag['class'] = 'tswv-image'
						if int(channel['channel_flag_password']) == 1:
							status_tag['class'] += ' tswv-channel-password'
						elif int(channel['total_clients']) == int(channel['channel_maxclients']):
							status_tag['class'] += ' tswv-channel-full'
						else:
							status_tag['class'] += ' tswv-channel-normal'
						status_tag.append('&nbsp;')
						channel_tag.append(status_tag)
						# Label
						label_tag = soup.new_tag('span')
						label_tag['class'] = 'tswv-label'
						label_tag.append(channel['channel_name'])
						channel_tag.append(label_tag)
						# Clients
						channel_tag, channel_clients = construct_clients(channel_tag, channel['cid'])
						# Recurse through sub-channels, collecting total number of clients as we go
						channel_tag, sub_clients = construct_channels(channel_tag, channel['cid'])
						channel_clients += sub_clients
						# Only show non-empty channels
						if channel_clients > 0:
							parent_tag.append(channel_tag)
							num_clients += channel_clients
				return parent_tag, num_clients

			def construct_clients(parent_tag, cid):
				num_clients = 0
				for client in clientlist:
					if int(client['cid']) == int(cid):
						# Skip ServerQuery clients
						if int(client['client_type']) == 1: continue
						num_clients += 1
						client_tag = soup.new_tag('div')
						client_tag['class'] = 'tswv-client'
						# Status image
						status_tag = soup.new_tag('span')
						status_tag['class'] = 'tswv-image'
						if int(client['client_type']) == 1:
							status_tag['class'] += ' tswv-client-query'
						elif int(client['client_away']) == 1:
							status_tag['class'] += " tswv-client-away"
						elif int(client['client_input_muted']) == 1:
							status_tag['class'] += " tswv-client-input-muted"
						elif int(client['client_output_muted']) == 1:
							status_tag['class'] += " tswv-client-output-muted"
						elif int(client['client_input_hardware']) == 0:
							status_tag['class'] += " tswv-client-input-muted-hardware"
						elif int(client['client_output_hardware']) == 0:
							status_tag['class'] += " tswv-client-output-muted-hardware"
						elif (int(client['client_flag_talking']) == 1) and (int(client['client_is_channel_commander']) == 1):
							status_tag['class'] += " tswv-client-channel-commander-talking"
						elif int(client['client_is_channel_commander']) == 1:
							status_tag['class'] += " tswv-client-channel-commander"
						elif int(client['client_flag_talking']) == 1:	
							status_tag['class'] += " tswv-client-talking"
						else:
							status_tag['class'] += " tswv-client-normal"
						status_tag.append('&nbsp;')
						client_tag.append(status_tag)
						# Country image
						country_tag = soup.new_tag('span')
						country_tag['class'] = 'tswv-image tswv-image-right'
						country_tag['title'] = ' '.join([word.capitalize() for word in utils.ISO3166_MAPPING[client['client_country']].split(' ')])
						country_tag['style'] = 'background: url("%s") center center no-repeat;' % url_for('static', filename='img/ts3_viewer/countries/%s.png' % client['client_country'].lower())
						country_tag.append('&nbsp;')
						client_tag.append(country_tag)
						# Server group images
						sgids = [int(sg) for sg in client['client_servergroups'].split(',')]
						servergroups = [servergroup for servergroup in servergrouplist if int(servergroup['sgid']) in sgids]
						servergroups.sort(key=operator.itemgetter('sortid'))
						for servergroup in servergroups:
							if not servergroup['iconid']: continue
							img_fname = 'img/ts3_viewer/%s.png' % servergroup['iconid']
							if not os.path.exists(os.path.join(app.static_folder, img_fname)):
								continue
							image_tag = soup.new_tag('span')
							image_tag['class'] = 'tswv-image tswv-image-right'
							image_tag['title'] = servergroup['name']
							image_tag['style'] = 'background-image: url("%s")' % url_for('static', filename=img_fname)
							image_tag.append('&nbsp;')
							client_tag.append(image_tag)
						# Check if client is in a moderated channel
						channel = [channel for channel in channellist if int(channel['cid']) == int(client['cid'])][0]
						if int(channel['channel_needed_talk_power']) > 0:
							status_tag = soup.new_tag('span')
							status_tag['class'] = 'tswv-image tswv-image-right'
							if int(client['client_is_talker']) == 0:
								status_tag['class'] += ' tswv-client-input-muted'
							else:
								status_tag['class'] += ' tswv-client-talkpower-granted'
							status_tag.append('&nbsp;')
							client_tag.append(status_tag)
						# Label
						label_tag = soup.new_tag('span')
						label_tag['class'] = 'tswv-label'
						label_tag.append(client['client_nickname'])
						client_tag.append(label_tag)
						parent_tag.append(client_tag)
				return parent_tag, num_clients
			div_tag, num_clients = construct_channels(div_tag, 0)
			return soup.prettify()
		except Exception as inst:
			return "error: %s" % inst
	def shorten_text(text, num_words=10):
		text = utils.fix_bad_unicode(text)
		space_iter = re.finditer('\s+', text)
		output = u''
		while num_words > 0:
			match = space_iter.next()
			if not match: break
			output = text[:match.end()]
			num_words -= 1
		else:
			output += '...'
		return output
	def num_unique_clients(teamspeak_data):
		unique_clients = set()
		for data in teamspeak_data:
			unique_clients.update(data.clients)
		return len(unique_clients)
	def num_unique_clients_by_country(teamspeak_data):
		unique_clients = {}
		for data in teamspeak_data:
			for client_id, client_data in data.clients.iteritems():
				unique_clients[client_id] = (client_data['country'] or 'Unknown').lower()
		country = {}
		for client_id, country_code in unique_clients.iteritems():
			country[country_code] = country.get(country_code, 0) + 1
		return country
	def country_abbreviation_mapping():
		mapping = {}
		for key, name in utils.ISO3166_MAPPING.iteritems():
			mapping[key.lower()] = ' '.join([word.capitalize() for word in name.split(' ')])
		return mapping
	return dict(timestamp_to_js_date=utils.timestamp_to_js_date, ts3_viewer=ts3_viewer, shorten_text=shorten_text, getTeamspeakWindow=doob.getTeamspeakWindow,
			num_unique_clients=num_unique_clients,
			num_unique_clients_by_country=num_unique_clients_by_country,
			country_abbreviation_mapping=country_abbreviation_mapping)
			
			
			'''
