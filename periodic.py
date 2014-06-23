import os

os.chdir(os.path.abspath(os.path.split(__file__)[0]))
activate_this = os.path.join(os.path.split(__file__)[0], 'venv', 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import ts3
from datetime import datetime, timedelta
from app import app, db, models

def idle_mover(server, cfg):
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
        if clientinfo.is_successful:
            client['client_unique_identifier'] = clientinfo.data[0]['client_unique_identifier']
        else:
            raise UserWarning('Could not find the clientinfo for %s' % client['clid'])

    # move idlers to afk channel
    for client in clientlist:
        if( int(client['client_idle_time']) > cfg['TS3_MAX_IDLETIME']):
            if client['cid'] not in exempt_cids:
                # Have TeamSpeak move AFK user to appropriate channel
                server.send_command('clientmove', keys={'clid': client['clid'], 'cid': afk_channel['cid']})

def store_active_data(server, cfg):
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

def process_ts3_events(server, cfg):
    # Get list of clients
    clientlist = server.clientlist()
    for clid, client in clientlist.iteritems():
        clientinfo = server.send_command('clientinfo', {'clid':clid})
        if clientinfo.is_successful:
            client['client_unique_identifier'] = clientinfo.data[0]['client_unique_identifier']
        else:
            raise UserWarning('Could not find clientinfo for %s' % clid)

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

def award_idle_ts3_points(server, cfg):
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
            else:
                raise UserWarning('Could not find the clientinfo for %s' % clid) 

        # Update the data
        active_users = set() 
        for client in clientlist.values():
            with open('clientlist.txt', 'ab') as f:
                f.write(client['client_nickname']+'\n\r\t'+\
                        client['client_unique_identifier']+'\n\r')
            if client['cid'] not in exempt_cids:
                doob = models.User.query.filter_by(teamspeak_id=client['client_unique_identifier']).first()
                if doob:
                    doob.update_connection()
                    active_users.add(doob)
        doobs = set(models.User.query.filter(models.User.ts3_starttime != None).all())
        print doobs, active_users
        for doob in doobs.intersection(active_users):
            print(doob.nickname)
            #doob.finalize_connection() 


if __name__ == "__main__":
    cfg = {}
    cfg = app.config

    server = ts3.TS3Server(cfg['TS3_HOST'], cfg['TS3_PORT'])
    server.login(cfg['TS3_USERNAME'], cfg['TS3_PASSWORD'])
    server.use(1)

    idle_mover(server, cfg)
    store_active_data(server, cfg)
    process_ts3_events(server, cfg)
    award_idle_ts3_points(server, cfg)
