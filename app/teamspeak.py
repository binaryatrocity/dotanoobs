from flask import url_for
from operator import itemgetter
from os import path
import ts3
from datetime import datetime, timedelta
from xml.etree import ElementTree
from bs4 import BeautifulSoup

import models
from app import app, db

def getTeamspeakWindow(window=timedelta(weeks=1)):
    current_time = datetime.utcnow()
    return models.TeamspeakData.query.filter(models.TeamspeakData.time < current_time, models.TeamspeakData.time > current_time-window).order_by(models.TeamspeakData.time).all()

def registerUserTeamspeakId(user, tsid):
    server = ts3.TS3Server(app.config['TS3_HOST'], app.config['TS3_PORT'])
    server.login(app.config['TS3_USERNAME'], app.config['TS3_PASSWORD'])
    server.use(1)

    response = server.send_command('clientdbfind', {'pattern':tsid.encode('utf-8')}, ('uid',))
    if response.is_successful:
        cdbid = response.data[0]['cldbid']
        user.teamspeak_id = tsid
        sgid = [entry['sgid'] for entry in server.send_command('servergrouplist').data if entry['name'] == 'Normal' and entry['type'] == '1'][0]
        server.send_command('servergroupaddclient', {'sgid': sgid, 'cldbid': cdbid})
        db.session.commit()
        return True
    return False

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
                                    servergroups.sort(key=itemgetter('sortid'))
                                    for servergroup in servergroups:
                                            if not servergroup['iconid']: continue
                                            img_fname = 'img/ts3_viewer/%s.png' % servergroup['iconid']
                                            if not path.exists(path.join(app.static_folder, img_fname)):
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
    with open(path.join(path.dirname(__file__), 'static/country_codes.xml'), mode='r') as d:
        data = d.read()
    xml = ElementTree.fromstring(data)
    d = dict()
    for entry in xml.findall('ISO_3166-1_Entry'):
        d[entry.find('ISO_3166-1_Alpha-2_Code_element').text] = entry.find('ISO_3166-1_Country_name').text
    return d

ISO3166_MAPPING = get_ISO3166_mapping()

#
# Scheduled functions for TeamspeakServer
#

def idle_mover(server):
    """ Checks connected clients idle_time, moving to AFK if over TS3_MAX_IDLETIME. """

    app.logger.debug("Running TS3 AFK mover...")
    exempt_cids = []
    permid_response = server.send_command('permidgetbyname', keys={'permsid': 'i_channel_needed_join_power'})
    if permid_response.is_successful:
        join_permid = permid_response.data[0]['permid']
    def exempt_check(cid):
        # check flags
        flag_response = server.send_command('channelinfo', keys={'cid': cid})
        if flag_response.is_successful:
            if flag_response.data[0]['channel_needed_talk_power'] != '0': return True
        permid_response = server.send_command('channelpermlist', keys={'cid': cid})
        if permid_response.is_successful:
            for perm in permid_response.data:
                if perm['permid'] == join_permid and perm['permvalue'] != '0': return True
        return False
    list_response = server.send_command('channellist')
    if list_response.is_successful:
        for channel in list_response.data:
            if exempt_check(channel['cid']):
                exempt_cids.append(channel['cid'])

    # get destination
    response = server.send_command('channelfind', keys={'pattern': 'AFK'})
    if response.is_successful:
        afk_channel = response.data[0]

    # Get list of clients
    clientlist = server.send_command('clientlist', opts=['times']).data
    for client in clientlist:
        clientinfo = server.send_command('clientinfo', {'clid':client['clid']})
        #if clientinfo.is_successful:
            #client['client_unique_identifier'] = clientinfo.data[0]['client_unique_identifier']

    # move idlers to afk channel
    for client in clientlist:
        if( int(client['client_idle_time']) > app.config['TS3_MAX_IDLETIME']):
            if client['cid'] not in exempt_cids:
                # Have TeamSpeak move AFK user to appropriate channel
                server.send_command('clientmove', keys={'clid': client['clid'], 'cid': afk_channel['cid']})

def store_active_data(server):
        """ Take a snapshot of Teamspeak (clients, countries, etc) to feed the ts3_stats page """

        app.logger.debug("Taking Teamspeak snapshot...")
        # Get exempt channels (AFK, passworded, join powers)
        exempt_cids = []
        permid_response = server.send_command('permidgetbyname', keys={'permsid': 'i_channel_needed_join_power'})
        if permid_response.is_successful:
            join_permid = permid_response.data[0]['permid']
        def exempt_check(cid):
            # Check flags
            flag_response = server.send_command('channelinfo', keys={'cid': cid})
            if flag_response.is_successful:
                if flag_response.data[0]['channel_flag_password'] != '0': return True
                if flag_response.data[0]['channel_needed_talk_power'] != '0': return True
            permid_response = server.send_command('channelpermlist', keys={'cid': cid})
            if permid_response.is_successful:
                for perm in permid_response.data:
                    if perm['permid'] == join_permid and perm['permvalue'] != '0': return True
            return False
        list_response = server.send_command('channellist')
        if list_response.is_successful:
            for channel in list_response.data:
                if exempt_check(channel['cid']):
                    exempt_cids.append(channel['cid'])

        # Get list of clients
        clientlist = server.send_command('clientlist', opts=("country",)).data
        # Remove the server_query and afk/moderated clients
        clientlist = filter(lambda client: client['client_type'] == '0' and client['cid'] not in exempt_cids, clientlist)
        # Compile the important information
        clients = {}
        for client in clientlist:
                clientinfo = server.send_command('clientdbinfo', {'cldbid': client['client_database_id']})
                if clientinfo.is_successful:
                        clients[clientinfo.data[0]['client_unique_identifier']] = {'country': client['client_country']}
                else:
                        raise UserWarning('Could not find the clientdbinfo for %s' % client['client_database_id'])

        # Update the data
        tsdata = models.TeamspeakData(clients)
        db.session.add(tsdata)
        db.session.commit()

def process_ts3_events(server):
    """ Create Teamspeak channels for upcoming events, delete empty event channels that have expired """

    app.logger.debug("Processing Teamspeak events...")
    # Get list of clients
    clientlist = server.clientlist()
    for clid, client in clientlist.iteritems():
        clientinfo = server.send_command('clientinfo', {'clid':clid})
        if clientinfo.is_successful:
            client['client_unique_identifier'] = clientinfo.data[0]['client_unique_identifier']

    # Process any active events
    for clid, client in clientlist.iteritems():
        u = models.User.query.filter_by(teamspeak_id=client['client_unique_identifier']).first()
        e = models.Event.query.filter(models.Event.start_time <= datetime.utcnow(), models.Event.end_time > datetime.utcnow()).all()
        if u and e:
            for event in e:
                if client['cid'] in event.cids:
                    event.add_participant(u)
    
    # Add channels for upcoming events
    e = models.Event.query.filter(models.Event.start_time >= datetime.utcnow(), \
            models.Event.start_time <= (datetime.utcnow() + timedelta(minutes=60))).all()
    for event in e:
        if not event.cids:
            print("Adding channels for event {}".format(event.name))
            event.create_channels()

    # Remove channels for expired events
    e = models.Event.query.filter(models.Event.start_time > (datetime.utcnow() - timedelta(hours=24)), \
            models.Event.end_time < (datetime.utcnow() - timedelta(minutes=60))).all()
    for event in e:
        current_time = datetime.utcnow()
        remove_time = event.end_time + timedelta(minutes=60)
        warn_time = event.end_time + timedelta(minutes=30)
        time_left = remove_time - current_time
        message = "This event channel is temporary and will be removed in {} minutes.".format(divmod(time_left.days * 86400 + time_left.seconds, 60)[0])
        if event.cids:
            if current_time > remove_time:
                print("Removing channels for event: {}".format(event.name))
                event.remove_channels()
            elif current_time > warn_time:
                for cid in event.cids:
                    clients = [client for client in clientlist.values() if int(client['cid']) == int(cid)]
                    for client in clients:
                        print("Warning {} about expired event {}".format(client['client_nickname'], event.name))
                        server.clientpoke(client['clid'], message)


def award_idle_ts3_points(server):
        """ Award points for active time spent in the Teamspeak server. """

        app.logger.debug("Awarding Teamspeak idle points")
        # Get exempt channels (AFK, passwords, join power)
        exempt_cids = []
        permid_response = server.send_command('permidgetbyname', keys={'permsid': 'i_channel_needed_join_power'})
        if permid_response.is_successful:
            join_permid = permid_response.data[0]['permid']
        def exempt_check(cid):
            # Check flags
            flag_response = server.send_command('channelinfo', keys={'cid':cid})
            if flag_response.is_successful:
                if flag_response.data[0]['channel_flag_password'] != '0': return True
                if flag_response.data[0]['channel_needed_talk_power'] !='0': return True
            permid_response = server.send_command('channelpermlist', keys={'cid': cid})
            if permid_response.is_successful:
                for perm in permid_response.data:
                    if perm['permid'] == join_permid and perm['permvalue'] != '0': return True
            return False
        list_response = server.send_command('channellist')
        if list_response.is_successful:
            for channel in list_response.data:
                if exempt_check(channel['cid']):
                    exempt_cids.append(channel['cid'])
        # Get list of clients
        clientlist = server.clientlist()
        for clid, client in clientlist.iteritems():
            clientinfo = server.send_command('clientinfo', {'clid': clid})
            if clientinfo.is_successful:
                client['client_unique_identifier'] = clientinfo.data[0]['client_unique_identifier']

        # Update the data
        active_users = set() 
        for client in clientlist.values():
            if client['cid'] not in exempt_cids:
                try:
                    doob = models.User.query.filter_by(teamspeak_id=client['client_unique_identifier']).first()
                    if doob:
                        doob.update_connection()
                        active_users.add(doob)
                except KeyError:
                    pass
        doobs = set(models.User.query.filter(models.User.ts3_starttime != None).all())
        for doob in doobs.intersection(active_users):
            doob.finalize_connection() 
