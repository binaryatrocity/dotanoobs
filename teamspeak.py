import operator
import os
import ts3
import time
import requests
from xml.etree import ElementTree
from flask import url_for
from bs4 import BeautifulSoup

from app import app
from models import TeamspeakData

def getTeamspeakWindow(window=605800):
    current_time = time.time()
    return TeamspeakData.query.filter(TeamspeakData.time < current_time, TeamspeakData.time > current_time-window).order_by(TeamspeakData.time).all()

def create_teamspeak_viewer():
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
                                            pass
                                    image_tag.append(' ')
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
                                    status_tag.append(' ')
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
                                    status_tag.append(' ')
                                    client_tag.append(status_tag)
                                    # Country image
                                    if client['client_country']:
                                            country_tag = soup.new_tag('span')
                                            country_tag['class'] = 'tswv-image tswv-image-right'
                                            country_tag['title'] = ' '.join([word.capitalize() for word in ISO3166_MAPPING[client['client_country']].split(' ')])
                                            country_tag['style'] = 'background: url("%s") center center no-repeat;' % url_for('static', filename='img/ts3_viewer/countries/%s.png' % client['client_country'].lower())
                                            country_tag.append(' ')
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
                                            image_tag.append(' ')
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
                                            status_tag.append(' ')
                                            client_tag.append(status_tag)
                                    # Label
                                    label_tag = soup.new_tag('span')
                                    label_tag['class'] = 'tswv-label'
                                    label_tag.append(client['client_nickname'])
                                    client_tag.append(label_tag)
                                    parent_tag.append(client_tag)
                    return parent_tag, num_clients
            div_tag, num_clients = construct_channels(div_tag, 0)
            return (soup.prettify(), num_clients)
    except Exception as inst:
            return "error: %s" % inst

def get_ISO3166_mapping():
    data = requests.get('http://www.iso.org/iso/home/standards/country_codes/country_names_and_code_elements_xml.html')
    xml = ElementTree.fromstring(data.text.encode('utf-8'))
    d = dict()
    for entry in xml.findall('ISO_3166-1_Entry'):
        d[entry.find('ISO_3166-1_Alpha-2_Code_element').text] = entry.find('ISO_3166-1_Country_name').text
    return d

ISO3166_MAPPING = get_ISO3166_mapping()


