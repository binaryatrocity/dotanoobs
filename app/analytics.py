import requests
from time import sleep, mktime
from bs4 import BeautifulSoup
from datetime import datetime

from app import app, db, models

MODES_TO_SKIP = ['Ability Draft', 'Greeviling', 'Diretide']

def collect_match_results(dotabuff_id, num_matches):
    results = []
    page = 0
    while True:
        page += 1
        url = "http://dotabuff.com/players/{}/matches/?page={}".format(dotabuff_id, page)
        data = requests.get(url).text
        soup = BeautifulSoup(data).article.table.tbody
        # Catch last page
        if 'sorry' in soup.tr.td.text.lower():
            break
        # Parse the matches on current page
        for row in soup.find_all('tr'):
            # Pass over bot matches and other 'inactive' games
            if 'inactive' in row.get('class', ''): continue
            cells = row.find_all('td')
            result_cell = cells[2]
            match_cell = cells[3]
            match_id = int(result_cell.a['href'].split('/')[-1])
            match_type = match_cell.div.text
            if match_type in MODES_TO_SKIP: continue
            result = True if 'won' in result_cell.a['class'] else False
            dt = datetime.strptime(result_cell.time['datetime'], '%Y-%m-%dT%H:%M:%S+00:00')
            results.append({'match_id':match_id, 'win':result, 'datetime':dt, 'game_mode':match_type})
            if len(results) > num_matches:
                break
        if len(results) > num_matches:
            break
        sleep(60)
    results.reverse()
    return results

def apply_window(results, window_size=50):
    windows = []
    # Compute the initial window
    win_rate = 0.00
    for idx in range(0, window_size):
        win_rate += 1 if results[idx]['win'] else 0
    win_rate /= window_size
    windows.append(win_rate)
    # From here on, modify based on leave/enter data points
    fractional_change = 1. / window_size
    for idx in range(window_size, len(results)):
        if results[idx-window_size]['win'] == results[idx]['win']:
            pass
        elif results[idx]['win']:
            win_rate += fractional_change
        else:
            win_rate -= fractional_change
        windows.append(win_rate)
    return windows

def calculate_winrates():
    users_analyzed = 0
    for user in models.User.query.all():
        db_id = requests.get("http://dotabuff.com/search?q="+user.steam_id).url.split("/")[-1]
        result = collect_match_results(db_id, app.config['ANALYTICS_WINRATE_NUM_MATCHES'])
        windowed = apply_window(result, app.config['ANALYTICS_WINRATE_WINDOW'])
        date_nums = map(lambda x: mktime(x['datetime'].timetuple()),\
                result[app.config['ANALYTICS_WINRATE_WINDOW']-1:])
        winrate = {'total_games': len(result), 'data': zip(date_nums, windowed) }
        user.winrate_data = winrate
        db.session.commit()
        users_analyzed += 1
        sleep(60)
    app.logger.info("Calculated win rate numbers for {} doobs.".format(users_analyzed))
    return users_analyzed
