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

from flask import Flask, abort, current_app, g, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from lxml import etree
from sqlalchemy import util
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
current_app.visibleLog = False
current_app.adminCode = random.randint(0, 1000000000)

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
AI.registerNoneFunction(func.vagueRequest)
# 向AI注册有多个匹配项时采用的函数
AI.registerMultipleFunction(func.vagueRequest)
# 向AI注册其他功能的函数
AI.registerPattern(interpreter.pIam, func.processIam)
AI.registerPattern(interpreter.pReserve, func.processReservation)
AI.registerPattern(interpreter.pCancel, func.processCancel)
AI.registerPattern(interpreter.pQuery, func.processQuery)
AI.registerPattern(interpreter.pAbout, func.about)
AI.registerPattern(interpreter.pEasterEgg, func.easterEgg)
AI.registerPattern(interpreter.pHelp, func.help)
AI.registerPattern(interpreter.pFrequent, func.)
AI.registerPattern(interpreter.pCheckLog, func.checkLog)

# 微信段设置的token，用于验证服务器是否正确运行
wxToken = 'bigchord'

# SQLAlchemy是一个数据库的ORM框架,即通过构建类的形式来操作数据库,不需要写sql语句
# 在SQLAlchemy中,表格以类的形式存在,数据项以对象的形式存在,增删查改均通过构建对话session来进行
# 了解数据库基本知识和SQLAlchemy的基本语法,对通读代码有很大的帮助

appPath = '/klavx/'

'''Flask的回调接口？'''
@app.route(appPath, methods=['GET', 'POST'])
def index() :
	authenticateMessage()
	if checkEcho() :
		return request.args['echostr']
	res = processMessage()
	return res

@app.route(appPath+'admin/', methods=['GET', 'POST'])
def admin() :
	getCode = int(request.args['code'])
	if getCode != current_app.adminCode :
		utils.writeLog('<Error>', 'Unauthorized user is trying to access background.', '0')
		return 'FUCK YOU!'
	else :
		utils.writeLog('<Background>', 'Authorized user is trying to access background.', '0')
		lastLogs = db.Logs.query.order_by(db.Logs.id.desc()).limit(200).all()
		result = '</br></br>'.join([str(s) for s in lastLogs]).replace('\n', '</br>')
		return result
	


# 验证是否是从微信服务器发来的请求
def authenticateMessage():
	try:
		s = ''.join(sorted([wxToken, request.args['timestamp'], request.args['nonce']]))
		if hashlib.sha1(s.encode('ascii')).hexdigest() == request.args['signature']:
			#succeeded, pass through
			return None
	except KeyError:
		# 如果不是微信服务器发来的请求，则认为是非法请求
		abort(BAD_REQUEST)


# 响应微信公众号配置页面发起的验证服务器请求
def checkEcho():
	if 'echostr' in request.args:
		return True
	return False


# 后台接受信息，对收到的xml进行解析后得到msgReceived，再将其转发给函数processText做进一步处理
# 关于后台收到的消息的XML数据包结构，可以参考微信官方网页：
# https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Receiving_standard_messages.html
def processMessage():
	try: e = etree.fromstring(request.data) #etree: html解析工具
	except etree.XMLSyntaxError: abort(BAD_REQUEST)

	ToUserName = e.findtext('ToUserName')
	FromUserName = e.findtext('FromUserName')
	CreateTime = e.findtext('CreateTime')
	Content = e.findtext('Content')
	MsgType = e.findtext('MsgType')
	MsgId = e.findtext('MsgId')
	Recognition = e.findtext('Recognition')

	if MsgType == 'voice' :
		Content = Recognition.replace('。', '')

	g.openId = FromUserName
	msgReceived = dict(ToUserName=ToUserName, FromUserName=FromUserName, CreateTime=CreateTime,
		Content=Content)
	
	utils.writeLog('Receive', utils.dict2Str(msgReceived), '0')

	replyDict = dict(ToUserName=FromUserName,
		FromUserName=ToUserName,
		CreateTime=CreateTime,
		MsgType='text')

	# MsgType为event表示服务器收到事件推送，如果event的值为subscribe，即有用户关注了北大钢琴社的
	# 公众号，则生成replyDict，将其转换为相应的xml格式并返回
	if MsgType.lower()=='event' :
		if e.findtext('Event').lower()=='subscribe':
			replyDict['Content'] = '感谢关注钢琴社公众号~，快输入“你好”跟我打招呼吧！'
		else :
			replyDict['Content'] = ''
	
	elif MsgId is None :
		# 鬼知道发生什么了，微信最近总是给我们发奇怪的消息，在这里加了几个过滤
		# 2021.10.25
		replyDict['Content'] = '奇怪的错误发生了\n'

	# 用户发来的是文本或语音
	elif MsgType in ('text','voice'):
		try:
			# 鬼知道发生什么了，微信最近总是给我们发奇怪的消息，在这里加了几个过滤
			# 之前加的似乎没用，又崩了一次
			# 2021.11.7
			if db.Message.query.filter_by(msgId=int(MsgId)).first() is not None :
				raise Exception('消息已处理，或者不存在MsgId')
			db.db.session.add(db.Message(msgId=int(MsgId)))
			db.db.session.commit()
		except Exception as e:
			# 鬼知道发生什么了，微信最近总是给我们发奇怪的消息，在这里加了几个过滤
			# 2021.10.25
			replyDict['Content'] = '奇怪的错误发生了\n'+str(e)
		else :
			# 是一条正常的文字消息或语音消息
			replyDict['Content'] = processText(Content)
	
	# 用户发来的消息不是文本也不是语音（比如图片），就根据微信的要求来返回错误提示
	else :
		replyDict['Content'] = '小AI暂时无法理解这类信息呢~'
	
	utils.writeLog('Reply', utils.dict2Str(replyDict), '0')
	return etree.tostring(utils.toEtree(replyDict), encoding='utf8')

def processText(Content):
	reply = None

	# 调用AI.doInterprete来处理内容，转换为相应的etree:reply
	try:
		reply = AI.doInterprete(Content)
	except Exception as e:
		reply = str(e)

	return reply

if __name__=='__main__':

	current_app.visibleLog = True

	# 刷新钢琴课命令: 进入命令行输入`sudo python main.py refreshcourses <filename>`
	if sys.argv[1]=='refreshcourses' :
		fileName = 'courses.txt'
		if len(sys.argv)==3 :
			fileName = sys.argv[2]
		if input("Old courses will be deleted. Are you sure? ") in ['Y','y','YES','Yes','yes'] :
			func.refreshCourses(fileName)
			print('done')
		else:
			print('aborted')

	# 添加演奏部成员：`sudo python main.py authorize <filename>`
	elif sys.argv[1]=='authorize' :
		fileName = 'perform.txt'
		if len(sys.argv)==3 :
			fileName = sys.argv[2]
		with open(sys.argv[2], 'r') as file:
			while True:
				line = file.readline()
				if not line :
					break
				line = line.replace('\n', '').replace(' ', '')
				func.authorizeUsers(line)
	
	elif len(sys.argv)==2 and sys.argv[1]=='admin' :
		print('Give admin permission to users name:')
		name = input()
		func.makeAdmin(name)
	
	elif len(sys.argv)==3 and sys.argv[1]=='show' :
		if sys.argv[2] == 'User' :
			func.showDatabase(db.User)
		elif sys.argv[2] == 'Course' :
			func.showDatabase(db.Course)
	
	else :
		Manager(app).run()
