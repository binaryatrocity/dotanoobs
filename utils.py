import requests
import re
from time import strptime, strftime, gmtime
from calendar import timegm
from app import app, cache
from teamspeak import create_teamspeak_viewer, getTeamspeakWindow, ISO3166_MAPPING

def get_steam_userinfo(steam_id):
	options = {
		'key': app.config['DOTA2_API_KEY'],
		'steamids': steam_id
	}
	data = requests.get('http://api.steampowered.com/ISteamUser/' \
						'GetPlayerSummaries/v0001/', params=options).json()
	return data['response']['players']['player'][0] or {}

# For Templates
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

@app.context_processor
def utility_processor():
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
    def timestamp_to_js_date(timestamp):
        return strftime('%B %d, %Y %H:%M:%S UTC', gmtime(timestamp))
    def js_date_to_timestamp(date):
        return timegm(strptime(date, '%s, %d %b %Y %H:%M:%S %Z'))
    return dict(ts3_viewer=ts3_viewer, ts3_current_clients=ts3_current_clients, get_teamspeak_window=get_teamspeak_window, \
            ts3_active_clients=ts3_active_clients, timestamp_to_js_date=timestamp_to_js_date, js_date_to_timestamp=js_date_to_timestamp, \
            num_unique_clients_by_country=num_unique_clients_by_country, country_abbreviation_mapping=country_abbreviation_mapping, \
            ts3_countries_active=ts3_countries_active)
