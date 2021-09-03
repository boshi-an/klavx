#!/usr/bin/python3
# vim: set noet ts=4 sw=4 fileencoding=utf-8:

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
from lxml import etree
from sqlalchemy.exc import IntegrityError

from exception import MyException

# 使用Flask构建web对象app
app = Flask(__name__)
# 激活app环境(with app_context()也行)
app.app_context().push()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True
app.logger.setLevel('ERROR')

import database as db
import functions as func
import interpreter
import utils

# 定义自定义解释器：“自主意识自然语言人工智能集群”，简称“AI”
# 该解释器初始化后可以理解部分微信消息
# 可以向该解释器注册函数，解释器将按照理解调用你的函数
interpreter.initPatterns()
AI = interpreter.TextInterpreter()
# 向AI注册在没有匹配项时采用的函数
AI.registerNoneFunction(func.randomEmoji)
AI.registerMultipleFunction(func.vagueRequest)
AI.registerPattern(interpreter.pIam, func.processIam)
AI.registerPattern(interpreter.pReserve, func.processReservation)
AI.registerPattern(interpreter.pCancel, func.processCancel)
AI.registerPattern(interpreter.pQuery, func.processQuery)
AI.registerPattern(interpreter.pAbout, func.about)
AI.registerPattern(interpreter.pEasterEgg, func.easterEgg)
AI.registerPattern(interpreter.pHelp, func.help)

# 微信段设置的token，用于验证服务器是否正确运行
wxToken = 'bigchord'

# SQLAlchemy是一个数据库的ORM框架,即通过构建类的形式来操作数据库,不需要写sql语句
# 在SQLAlchemy中,表格以类的形式存在,数据项以对象的形式存在,增删查改均通过构建对话session来进行
# 了解数据库基本知识和SQLAlchemy的基本语法,对通读代码有很大的帮助

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
	utils.printDict("receive", msgReceived)

	if e.findtext('MsgType').lower()=='event' and e.findtext('Event').lower()=='subscribe':
		replyDict = dict(ToUserName=e.findtext('FromUserName'),
			FromUserName=e.findtext('ToUserName'),
			CreateTime=e.findtext('CreateTime'))
		return etree.tostring(toEtree(replyDict), encoding='utf8')

	if e.findtext('MsgType') not in ('text','voice'):
		return

	try:
		db.db.session.add(db.Message(msgId=int(e.findtext('MsgId'))))
		db.db.session.commit()
	except IntegrityError:
		#消息已处理，或者不存在MsgId
		return ''

	return processText(**msgReceived)


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
		replyDict = dict(MsgType='text', Content=AI.doInterprete(Content))
	except MyException as e:
		replyDict = dict(MsgType='text', Content=e.args[0])

	reply = toEtree(dict(FromUserName=ToUserName, ToUserName=FromUserName, CreateTime=CreateTime))
	for k,v in replyDict.items():
		reply.append(toEtree(v, name=k))
	result = etree.tostring(reply, encoding='utf8')
	utils.printDict("reply", replyDict)
	return result

if __name__=='__main__':
	# 刷新钢琴课命令的入口
	if len(sys.argv)==2 and sys.argv[1]=='refreshcourses' :
		if input("Old courses will be deleted. Are you sure? ") in ['Y','y','YES','Yes','yes'] :
			function.refreshCourses()
			print('done')
		else:
			print('aborted')
	elif len(sys.argv)==3 and sys.argv[1]=='authorize' :
		with open(sys.argv[2], 'r') as file:
			while True:
				line = file.readline()
				if not line :
					break
				func.authorizeUsers(line)
	else :
		Manager(app).run()
