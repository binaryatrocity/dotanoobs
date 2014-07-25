#!venv/bin/python
from flask import Flask
from flask.ext.script import Manager, Server
from flask.ext.migrate import Migrate, MigrateCommand

from app import app, db, models

#SQLALCHEMY_DATABASE_URI = 'mysql://root:$perwePP@localhost/dotanoobs'

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

def createTeamspeakInstance():
    import ts3
    s = ts3.TS3Server(app.config['TS3_HOST'], app.config['TS3_PORT'])
    s.login(app.config['TS3_USERNAME'], app.config['TS3_PASSWORD'])
    s.use(1)
    return s

@manager.command
def install_cronjobs():
    from os import path
    from crontab import CronTab
    cron = CronTab(user=True)

    # Clear out existing jobs
    cron.remove_all(comment='DOOBSAUTO')

    def make_job(job):
        p = path.realpath(__file__)
        c = cron.new(command='{}/venv/bin/python {} {}'.format(path.split(p)[0],\
                p, job), comment='DOOBSAUTO')
        return c

    # Create the jobs
    winrate = make_job('calc_winrates')
    ts3_move_afk = make_job('ts3_move_afk')
    ts3_snapshot = make_job('ts3_snapshot')
    ts3_award_points = make_job('ts3_award_points')
    ts3_process_events = make_job('ts3_process_events')

    # Set their frequency to run
    winrate.every(1).day()
    ts3_move_afk.every(app.config['MOVE_AFK_FREQUENCY']).minute()
    ts3_snapshot.every(app.config['SNAPSHOT_FREQUENCY']).hour()
    ts3_award_points.every(app.config['AWARD_POINTS_FREQUENCY']).minute()
    ts3_process_events.every(app.config['PROCESS_EVENTS_FREQUENCY']).hour()

    try:
        assert True == winrate.is_valid()
        assert True == ts3_move_afk.is_valid()
        assert True == ts3_snapshot.is_valid()
        assert True == ts3_award_points.is_valid()
        assert True == ts3_process_events.is_valid()
    except AssertionError as e:
        print "Problem installing cronjobs: {}".format(e)
    else:
        cron.write()
        print "Cron jobs written succesfully"

@manager.command
def admin(name):
    u = models.User.query.filter_by(nickname=name).first()
    if u and not u.admin:
        u.admin = True
        db.session.commit()
        print "User {} has been granted admin access.".format(name)

@manager.command
def calc_winrates():
    from app.analytics import calculate_winrates
    calculate_winrates()

@manager.command
def ts3_move_afk():
    from app.teamspeak import idle_mover
    tsServer = createTeamspeakInstance()
    idle_mover(tsServer)

@manager.command
def ts3_snapshot():
    from app.teamspeak import store_active_data
    tsServer = createTeamspeakInstance()
    store_active_data(tsServer)

@manager.command
def ts3_award_points():
    from app.teamspeak import award_idle_ts3_points
    tsServer = createTeamspeakInstance()
    award_idle_ts3_points(tsServer)

@manager.command
def ts3_process_events():
    from app.teamspeak import process_ts3_events
    tsServer = createTeamspeakInstance()
    process_ts3_events(tsServer)


if __name__ == '__main__':
    manager.run()
