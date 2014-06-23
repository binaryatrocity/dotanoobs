#!venv/bin/python
import os
from flask import Flask
from flask.ext.script import Manager, Server
from flask.ext.migrate import Migrate, MigrateCommand

from app import *

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')

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
