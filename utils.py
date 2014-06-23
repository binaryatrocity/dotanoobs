import requests
import re
from time import strptime, strftime, gmtime
from bs4 import BeautifulSoup
from itertools import product
from os import path, makedirs

from calendar import timegm
from app import app, cache
from board import latest_news
from teamspeak import create_teamspeak_viewer, getTeamspeakWindow, ISO3166_MAPPING

def get_steam_userinfo(steam_id):
	options = {
		'key': app.config['DOTA2_API_KEY'],
		'steamids': steam_id
	}
	data = requests.get('http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0001/', params=options).json()
	return data['response']['players']['player'][0] or {}

def get_api_hero_data():
    data = requests.get("https://api.steampowered.com/IEconDOTA2_570/GetHeroes/v0001/?key="+app.config['DOTA2_API_KEY']+"&language=en_us").json()
    return data

API_DATA = get_api_hero_data()

def complete_hero_data(key, value):
    # Possible keys are id, localized_name and name
    for hero_data in API_DATA['result']['heroes']:
        if hero_data[key] == value: return hero_data

def get_hero_data_by_id(hero_id):
    return API_DATA['result']['heroes'][hero_id-1]

def parse_valve_heropedia():
    data = requests.get('http://www.dota2.com/heroes/')
    soup = BeautifulSoup(data.text)
    taverns = []
    tavern_names = [' '.join(entry) for entry in product(('Radiant', 'Dire'), ('Strength', 'Agility', 'Intelligence'))]
    for tavern_name, tavern in zip(tavern_names, soup.find_all(class_=re.compile('^heroCol'))):
        img_base = lambda tag: tag.name == 'img' and 'base' in tag.get('id')
        taverns.append((tavern_name, [complete_hero_data('name', 'npc_dota_hero_%s' % tag['id'].replace('base_', '')) for tag in tavern.find_all(img_base)]))
    return taverns

# For Templates
@app.template_filter('shorten')
def shorten_filter(s, num_words=40):
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

@app.template_filter('js_datetime')
def js_datetime(dt):
    return dt.strftime('%m %d %Y %H:%M')

@app.template_filter('event_badge')
def event_badge(t):
    if t == 'coaching':
        badge = "<div class='uk-badge'>Coaching</div>"
    elif t == 'inhouse':
        badge = "<div class='uk-badge uk-badge-success'>Inhouse</div>"
    elif t == 'tournament':
        badge = "<div class='uk-badge uk-badge-danger'>Tournament</div>"
    else:
        badge = "<div class='uk-badge uk-badge-warning'>Other</div>"
    return badge;

@app.context_processor
def utility_processor():
    ''' For Teamspeak '''
    @cache.memoize(60*5)
    def ts3_viewer():
        html = create_teamspeak_viewer()[0]
        return html
    @cache.memoize(60*5)
    def ts3_current_clients():
        num = create_teamspeak_viewer()[1]
        return num
    def get_teamspeak_window():
        data_list = getTeamspeakWindow()
        return data_list
    def ts3_active_clients(teamspeak_data):
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
    def ts3_countries_active(teamspeak_data):
        data = num_unique_clients_by_country(teamspeak_data)
        return len(data)
    def country_abbreviation_mapping():
        mapping = {}
        for key, name in ISO3166_MAPPING.iteritems():
            mapping[key.lower()] = ' '.join([word.capitalize() for word in name.split(' ')])
        return mapping
    ''' Dota2 info '''
    def total_hero_pool():
        return len(API_DATA['result']['heroes'])
    def hero_image_large(hero_data):
        if type(hero_data) is unicode:
            stripped_name = hero_data.replace('npc_dota_hero_', '')
        else:
            stripped_name = hero_data['name'].replace('npc_dota_hero_', '')
        img_file = path.join(app.config['HERO_IMAGE_PATH'], stripped_name + '.png')
        img_src = path.join(app.root_path, app.static_folder, img_file)
        if not path.exists(img_src):
            i = requests.get('http://media.steampowered.com/apps/dota2/images/heroes/{}_hphover.png'.format(stripped_name)).content
            if not path.exists(path.split(img_src)[0]):
                makedirs(path.split(img_src)[0])
            with open(img_src, 'wb') as img:
                img.write(i)
        return img_file
    def hero_image_small(hero_data):
        if type(hero_data) is unicode:
            stripped_name = hero_data.replace('npc_dota_hero_', '')
        else:
            stripped_name = hero_data['name'].replace('npc_dota_hero_', '')
        img_file = path.join(app.config['HERO_IMAGE_PATH'], stripped_name + '_small.png')
        img_src = path.join(app.root_path, app.static_folder, img_file)
        if not path.exists(img_src):
            i = requests.get('http://media.steampowered.com/apps/dota2/images/heroes/{}_sb.png'.format(stripped_name)).content
            if not path.exists(path.split(img_src)[0]):
                makedirs(path.split(img_src)[0])
            with open(img_src, 'wb') as img:
                img.write(i)
        return img_file
    ''' Misc '''
    def get_latest_news(num=3):
        return latest_news(num)
    return dict(ts3_viewer=ts3_viewer, ts3_current_clients=ts3_current_clients, get_teamspeak_window=get_teamspeak_window, \
            ts3_active_clients=ts3_active_clients, \
            num_unique_clients_by_country=num_unique_clients_by_country, country_abbreviation_mapping=country_abbreviation_mapping, \
            ts3_countries_active=ts3_countries_active, hero_image_large=hero_image_large, hero_image_small=hero_image_small, \
            heropedia=parse_valve_heropedia, total_hero_pool=total_hero_pool, get_latest_news=get_latest_news)
