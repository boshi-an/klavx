
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

# 使用Flask构建web对象app
app = Flask(__name__)
# 激活app环境(with app_context()也行)
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
	u = User.query
	for r in u :
		print(r)