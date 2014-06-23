#!venv/bin/python
from flask import Flask
from flask.ext.script import Manager, Server
from flask.ext.migrate import Migrate, MigrateCommand

from app import *

SQLALCHEMY_DATABASE_URI = 'mysql://root:$perwePP@localhost/dotanoobs'

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def admin(name):
    u = models.User.query.filter_by(nickname=name).first()
    if u and not u.admin:
        u.admin = True
        db.session.commit()
        print "User {} has been granted admin access.".format(name)

if __name__ == '__main__':
    manager.run()
