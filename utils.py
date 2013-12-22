import requests
from app import app

def get_steam_userinfo(steam_id):
	options = {
		'key': app.config['DOTA2_API_KEY'],
		'steamids': steam_id
	}
	data = requests.get('http://api.steampowered.com/ISteamUser/' \
						'GetPlayerSummaries/v0001/', params=options).json()
	return data['response']['players']['player'][0] or {}