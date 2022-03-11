# encoding=utf-8
import datetime
import hashlib
import os
import random
import re
import sqlite3
import sys
from http.client import BAD_REQUEST

from flask import Flask, abort, g, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from lxml import etree
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine

from exception import MyException

app = Flask(__name__)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True
app.logger.setLevel('ERROR')

from database import *

migrate = Migrate(app,db)
engine = create_engine('sqlite:///db', echo=False)

if __name__ == '__main__' :

	# this code uses to drop alembic_version, to avoid error 'Can't locate revision identified by'
	#sql = 'DROP TABLE IF EXISTS alembic_version ;'
	#result = engine.execute(sql)

	#this code uses to drop all logs
	# u = Logs.query.delete()
	# db.session.commit()
	# u = Logs.query.all()
	u = User.query.filter_by(openId='op3adjrNJMrRB5oWdvDbuSOkL6Kg')
	print(u.all())
	u.all()[0].name = "假的安博施"
	# u.authorized = 1

	db.session.commit()
