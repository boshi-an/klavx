#!/usr/bin/python3
# vim: set noet ts=4 sw=4 fileencoding=utf-8:

import os
import sys
import re
import random
import hashlib
import datetime
import sqlite3
from lxml import etree

from http.client import BAD_REQUEST
from flask import Flask, request, abort, g
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.exc import IntegrityError

import interpreter
import utils

# 使用Flask构建web对象app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True

# 微信段设置的token，用于验证服务器是否正确运行
wxToken = 'bigchord'
# SQLAlchemy是一个数据库的ORM框架,即通过构建类的形式来操作数据库,不需要写sql语句
# 在SQLAlchemy中,表格以类的形式存在,数据项以对象的形式存在,增删查改均通过构建对话session来进行
# 了解数据库基本知识和SQLAlchemy的基本语法,对通读代码有很大的帮助
db = SQLAlchemy(app)

class MyException(Exception):
	pass

# 存储所有收到的后台信息
class Message(db.Model):
	'timestamp 用来实现定期清除'
	msgId = db.Column(db.Integer(), primary_key=True, autoincrement=False)
	timestamp = db.Column(db.DateTime(), default=datetime.datetime.now, nullable=False)
	def __repr__(self):
		return '<Message {} at {}>'.format(self.msgId, self.timestamp)

# 用户类, name是用户输入的名字
class User(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	openId = db.Column(db.String(), unique=True, nullable=True) #null一般为手动录入但没登记的老师
	name = db.Column(db.String(), nullable=False)
	def __repr__(self):
		return '<User {} {}>'.format(self.openId, self.name)

# 登录信息
class Registration(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	openId = db.Column(db.String(), unique=True, nullable=False)
	name = db.Column(db.String(), nullable=False)
	def __repr__(self):
		return '<Registration {} {}>'.format(self.openId, self.name)

# 琴房信息,name是琴房的名字,B250,B252,B253
class Room(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	name = db.Column(db.String(collation='NOCASE'), unique=True, nullable=False)
	def __repr__(self):
		return '<Room {}>'.format(self.name)

# 预订琴房的信息
class Reservation(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	userId = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
	user = db.relationship('User', backref=db.backref('reservations', lazy='dynamic'))
	roomId = db.Column(db.Integer(), db.ForeignKey('room.id'), nullable=False)
	room = db.relation('Room', backref=db.backref('reservations', lazy='dynamic'))
	start = db.Column(db.DateTime(), nullable=False)
	end = db.Column(db.DateTime(), nullable=False)
	def __repr__(self):
		return '{} {}'.format(self.user.name, self.getDateRoom())

	def getDateRoom(self):
		return '{}年{}月{}日 {}:{:02}~{}:{:02} {}'.format(
				self.start.year, self.start.month, self.start.day,
				self.start.hour, self.start.minute,
				self.end.hour, self.end.minute,
				self.room.name)

# 钢琴课的信息
class Course(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	teacherId = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
	teacher = db.relation('User', backref=db.backref('courses', lazy='dynamic'))
	roomId = db.Column(db.Integer(), db.ForeignKey('room.id'), nullable=False)
	room = db.relation('Room', backref=db.backref('courses', lazy='dynamic'))
	weekday = db.Column(db.Integer(), nullable=False)
	startDate = db.Column(db.Date(), nullable=False)
	endDate = db.Column(db.Date(), nullable=False)
	startTime = db.Column(db.Time(), nullable=False)
	endTime = db.Column(db.Time(), nullable=False)
	def __repr__(self):
		return '<Course {} {}月{}日~{}月{}日 {} {}:{:02}~{}:{:02}>'.format(
				self.teacher.name,
				self.startDate.month, self.startDate.day,
				self.endDate.month, self.endDate.day,
				'周一 周二 周三 周四 周五 周六 周日'.split()[self.weekday],
				self.startTime.hour, self.startTime.minute,
				self.endTime.hour, self.endTime.minute)

admin = Admin(app)
admin.add_view(ModelView(Course, db.session))
admin.add_view(ModelView(Reservation, db.session))
admin.add_view(ModelView(Room, db.session))
admin.add_view(ModelView(Registration, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Message, db.session))

appPath = '/papuwx/'

'''Flask的回调接口？'''
@app.route(appPath, methods=['GET', 'POST'])
def index():
	
	authenticateMessage()
	if checkEcho() :
		return request.args['echostr']
	
	res = processMessage()
	return res


# 验证是否是从微信服务器发来的请求
def authenticateMessage():
	try:
		s = ''.join(sorted([wxToken, request.args['timestamp'], request.args['nonce']]))
		if hashlib.sha1(s.encode('ascii')).hexdigest() == request.args['signature']:
			#succeeded, pass through
			return None
	except KeyError:
		pass
	abort(BAD_REQUEST)


# 响应微信公众号配置页面发起的验证服务器请求
def checkEcho():
	if 'echostr' in request.args:
		return True
	return False

# 处理后台接受到的信息
def processMessage():
	try: e = etree.fromstring(request.data)#etree: html解析工具
	except etree.XMLSyntaxError: abort(BAD_REQUEST)

	msgReceived = {x:e.findtext(x) for x in
					'ToUserName FromUserName CreateTime Content Recognition'.split()}
	print("receive:",msgReceived)

	if e.findtext('MsgType').lower()=='event' and e.findtext('Event').lower()=='subscribe':
		replyDict = dict(ToUserName=e.findtext('FromUserName'),
			FromUserName=e.findtext('ToUserName'),
			CreateTime=e.findtext('CreateTime'))
		return etree.tostring(toEtree(replyDict), encoding='utf8')

	if e.findtext('MsgType') not in ('text','voice'):
		return

	try:
		db.session.add(Message(msgId=int(e.findtext('MsgId'))))
		db.session.commit()
	except IntegrityError:
		#消息已处理，或者不存在MsgId
		return ''

	return processText(**msgReceived)


# 返回一个随机的表情
def randomEmoji():
	available = [(0x1f31a,0x1f31e), (0x1f646,0x1f64f)]
	pos = random.randrange(sum(x[1]-x[0]+1 for x in available))
	for x in available:
		if pos < x[1]-x[0]+1:
			return chr(x[0]+pos)
		pos -= x[1]-x[0]+1

# Mark,昨天看代码看到这里
def toEtree(d, name='xml'):
	e = etree.Element(name)
	if isinstance(d, dict):
		for k,v in d.items():
			e.append(toEtree(v, name=k))
	elif isinstance(d, tuple) or isinstance(d, list):
		for k,v in d:
			e.append(toEtree(v, name=k))
	else:
		e.text = str(d)
	return e


def processText(ToUserName, FromUserName, CreateTime, Content, Recognition):
	g.openId = FromUserName
	Content = Content or Recognition
	try:
		replyDict = dict(MsgType='text', Content=randomEmoji())
	except MyException as e:
		replyDict = dict(MsgType='text', Content=e.args[0])

	reply = toEtree(dict(FromUserName=ToUserName, ToUserName=FromUserName, CreateTime=CreateTime))
	for k,v in replyDict.items():
		reply.append(toEtree(v, name=k))
	result = etree.tostring(reply, encoding='utf8')
	print("reply:", replyDict)
	return result

if __name__=='__main__':
	Manager(app).run()
