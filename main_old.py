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

import patterns
import music
from utils import currentDate, toDatetime

# 使用Flask构建web对象app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True

wxToken = 'bigchord'
# SQLAlchemy是一个数据库的ORM框架,即通过构建类的形式来操作数据库,不需要写sql语句
# 在SQLAlchemy中,表格以类的形式存在,数据项以对象的形式存在,增删查改均通过构建对话session来进行
# 了解数据库基本知识和SQLAlchemy的基本语法,对通读代码有很大的帮助
db = SQLAlchemy(app)


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

# 演奏者的信息,该功能已弃用
class Show(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	performerId = db.Column(db.Integer(), db.ForeignKey('user.id'), nullable=False)
	performer = db.relation('User', backref=db.backref('shows', lazy='dynamic'))
	def __repr__(self):
		return '<Show {}>'.format(self.performer)

# 推荐音乐的信息,该功能已弃用
class OnlineMusic(db.Model):
	id = db.Column(db.Integer(), primary_key=True)
	title = db.Column(db.String(), nullable=True)
	url = db.Column(db.String(), nullable=False, unique=True)
	def __repr__(self):
		return '<OnlineMusic {} {}>'.format(self.title, self.url)

admin = Admin(app)
admin.add_view(ModelView(OnlineMusic, db.session))
admin.add_view(ModelView(Show, db.session))
admin.add_view(ModelView(Course, db.session))
admin.add_view(ModelView(Reservation, db.session))
admin.add_view(ModelView(Room, db.session))
admin.add_view(ModelView(Registration, db.session))
admin.add_view(ModelView(User, db.session))
admin.add_view(ModelView(Message, db.session))

appPath = '/papuwx/' # if __name__=='__main__' else '/'

'''Flask的回调接口？'''
@app.route(appPath, methods=['GET', 'POST'])
def index():
	for func in processes:
		# $processes 是待处理项
		result = func()
		if result is not None:
			return result
	return ''


processes = []
def process(func):
	processes.append(func)


@process
def authenticateMessage():
	'验证是否是从微信服务器发来的请求'
	try:
		s = ''.join(sorted([wxToken, request.args['timestamp'], request.args['nonce']]))
		if hashlib.sha1(s.encode('ascii')).hexdigest() == request.args['signature']:
			#succeeded, pass through
			return None
	except KeyError:
		pass
	abort(BAD_REQUEST)


@process
def checkEcho():
	'响应微信公众号配置页面发起的验证服务器请求'
	if 'echostr' in request.args:
		return request.args['echostr']

# 处理后台接受到的信息
@process
def processMessage():
	print(request.data)
	try: e = etree.fromstring(request.data)#etree: html解析工具
	except etree.XMLSyntaxError: abort(BAD_REQUEST)

	if e.findtext('MsgType').lower()=='event' and e.findtext('Event').lower()=='subscribe':
		replyDict = dict(ToUserName=e.findtext('FromUserName'),
			FromUserName=e.findtext('ToUserName'),
			CreateTime=e.findtext('CreateTime'))
		replyDict.update(recommendMusic())
		return etree.tostring(toEtree(replyDict), encoding='utf8')
		return etree.tostring(toEtree(dict(ToUserName=e.findtext('FromUserName'),
			FromUserName=e.findtext('ToUserName'),
			CreateTime=e.findtext('CreateTime'),
			MsgType='text',
			Content='欢迎关注钢琴社公众号\n（づ￣3￣）づ╭❤～')), encoding='utf8')

	if e.findtext('MsgType') not in ('text','voice'):
		return

	try:
		db.session.add(Message(msgId=int(e.findtext('MsgId'))))
		db.session.commit()
	except IntegrityError:
		#消息已处理，或者不存在MsgId
		return ''

	return processText(**{x:e.findtext(x) for x in
					   'ToUserName FromUserName CreateTime Content Recognition'.split()})


# 返回一个随机的表情
def randomEmoji():
	available = [(0x1f31a,0x1f31e), (0x1f646,0x1f64f)]
	pos = random.randrange(sum(x[1]-x[0]+1 for x in available))
	for x in available:
		if pos < x[1]-x[0]+1:
			return chr(x[0]+pos)
		pos -= x[1]-x[0]+1

# 暂时没看懂在干嘛
def randomEmojiLink(emoji=None, link=None):
	if emoji is None:
		emoji = randomEmoji()
	if link is None:
		m = music.randomMusic()
		link = m['url']
	return '<a href="{}">{}</a>'.format(link, emoji)

# 从OnlineMusic表格中随机选出一首音乐
def randomMusic():
	n = OnlineMusic.query.count()
	music = OnlineMusic.query[random.randrange(n)]
	return music.url

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
		for function in processText.functions:
			replyDict = function(Content)
			if replyDict is not None: break
		else:
			replyDict = dict(MsgType='text', Content=randomEmoji())
			#if random.randrange(6)==0:
			#	replyDict = dict(MsgType='text',
			#			Content=randomEmojiLink())
			#else:
			#	replyDict = recommendMusic()
	except MyException as e:
		replyDict = dict(MsgType='text', Content=e.args[0])

	reply = toEtree(dict(FromUserName=ToUserName, ToUserName=FromUserName, CreateTime=CreateTime))
	for k,v in replyDict.items():
		reply.append(toEtree(v, name=k))
	result = etree.tostring(reply, encoding='utf8')
	print(result)
	return result


def recommendMusic():
	tryCount = 10
	nMusic = 3
	musics = {}
	for x in range(tryCount):
		if len(musics)==nMusic: break
		m = music.randomMusic()
		musics[m['url']] = m
	return dict(MsgType='news',
			ArticleCount=len(musics),
			Articles=[('item', dict(Title=m['title'], Url=m['url'], PicUrl=m['image']))
				for m in musics.values()])


def newTextFunc(func):
	processText.__dict__.setdefault('functions',[]).append(func)
	return func


@newTextFunc
def randMusicCommand(Content):
	if not Content.startswith('.music'): return
	url = 'http://www.xiami.com/song/1770656657?spm=a1z1s.3521865.23309997.11.5KmuQs'
	return {'MsgType':'text', 'Content':'<a href="{}">{}</a>'.format(url, randomEmoji())}
	return {'MsgType':'music', 'Music':{
		'Title':'TheTitle',
		'Description':'TheDescription',
		'MusicUrl':url,
		'HQMusicUrl':url,
		}}


def newTextToText(func):
	def newFunc(Content):
		#Content = re.sub('[,，。!！?？]', '', Content.strip())
		#if Content == '': return ''
		replyText = func(Content.strip())
		if replyText is None: return
		return dict(MsgType='text', Content=replyText)
	return newTextFunc(newFunc)


@newTextToText
def processCommand(message):
	if message.startswith('.addmusic'):
		parts = message.split()
		if parts[0]!='.addmusic' or len(parts)<3 or not parts[-1].startswith('http://'):
			return
		title = ' '.join(parts[1:-1])
		url = parts[-1]
		try:
			db.session.add(OnlineMusic(title=title, url=url))
			db.session.commit()
		except IntegrityError:
			return 'already existed'
		return 'done'


def message(patternEntry):
	def decorate(func):
		def newFunc(message):
			try:
				result = patternEntry(message)
				if result is None: return
				if result.__class__ in [tuple,list]:
					return func(*result)
				else:
					return func(result)
			except ValueError as e:
				return e.args[0]
		return newTextToText(newFunc)
	return decorate


class MyException(Exception):
	pass


def authenticated(func):
	def newFunc(*args, **kwargs):
		user = User.query.filter_by(openId=g.openId).first()
		if user is None:
			raise MyException('抱歉，您还没有登记。请发送 我是xxx')
		g.user = user
		return func(*args, **kwargs)
	return newFunc


def overlayedReservation(start, end, room=None):
	query = Reservation.query if room is None else room.reservations
	return query.filter(db.or_(
		db.and_(Reservation.start<start, Reservation.end>start), # ( [ )
		db.and_(Reservation.start>=start, Reservation.start<end)) # [ ( ]
	)


def overlayedCourse(start, end):
	end -= datetime.timedelta(microseconds=1)
	assert start.date() == end.date()

	return (Course.query.filter_by(weekday=start.weekday())
			.filter(db.and_(Course.startDate<=start.date(),
				Course.endDate>=start.date()))
			.filter(db.or_(
				db.and_(Course.startTime<start.time(), Course.endTime>start.time()),
				db.and_(Course.startTime>=start.time(), Course.startTime<=end.time()))))


def queryExist(query):
	return len(query[:1]) > 0


@message(patterns.iAm)
def processRegistration(name):
	user = User.query.filter_by(openId=g.openId).first()
	if user is not None:
		if user.name == name:
			return '您已设置姓名为 {}'.format(name)
		return '您已设置姓名为 {}，不可更改'.format(user.name)

	registration = Registration.query.filter_by(openId=g.openId).first()
	if registration is None:
		db.session.add(Registration(openId=g.openId, name=name))
		db.session.commit()
		return '您即将设置姓名为 {}。请再输入一次，请注意，一旦设置后不可更改。'.format(name)
	elif registration.name != name:
		db.session.delete(registration)
		db.session.commit()
		return '两次输入不一致，请重新输入'
	else:
		#如果当前仅有一个重名用户且此人没有openId，则将其视为预先录入的老师，二者为同一人
		users = User.query.filter_by(name=name).all()
		if len(users)==1 and users[0].openId is None:
			users[0].openId = g.openId
			db.session.add(users[0])
		else:
			db.session.add(User(openId=g.openId, name=name))
		db.session.delete(registration)
		db.session.commit()
		return '您已设置姓名为 {}'.format(name)


def getRoom(roomName):
	room = Room.query.filter_by(name=roomName).first()
	if room is None:
		raise MyException('没有找到 {} 琴房'.format(roomName))
	return room


@message(patterns.reservation)
@authenticated
def processReservation(start, end, roomName):
	if 0 and not queryExist(g.user.shows) and not queryExist(g.user.courses):
		return '抱歉，在5月21日演奏会之前，只有演员可以预约'

	if 1 and (start.month,start.day)==(6,4):
		return randomEmojiLink(emoji='\U0001F1E8\U0001F1F3', link='http://www.xiami.com/song/3598817')

	#活跃预约数不超过2
	nActiveReservations = (Reservation.query.filter_by(user=g.user)
			.filter(Reservation.start>datetime.datetime.now()).count())
	if nActiveReservations >= 2:
		return '抱歉，每人最多持有 2 个预约。如需添加新的预约，请取消至少一个预约。'

	#时长不超过2小时
	if (end-start).seconds > 2*3600:
		return '抱歉，单次预约时长不能超过 2 个小时。'

	room = None if roomName is None else getRoom(roomName)
	classRoom = Room.query.filter_by(name='B250').first()
	practiceRooms = [Room.query.filter_by(name=x).first() for x in ['B252', 'B253']]

	for x in [0]:
		roomFound = False

		for practiceRoom in practiceRooms:
			if room is None or room==practiceRoom:
				isIdle = not queryExist(overlayedReservation(start, end, practiceRoom))
				if isIdle:
					reservation = Reservation(user=g.user, room=practiceRoom, start=start, end=end)
					db.session.add(reservation)
					db.session.commit()
					roomFound = True
					break
		if roomFound: break

		if room is None or room==classRoom:
			#在本学期有课还没上完的时候，只有老师可以预约两天之后的classRoom
			if not ((queryExist(g.user.courses) #是老师
				or (start.date()-datetime.datetime.now().date()).days <= 2)):
				return '抱歉，只有教课的老师可以预约超过 2 天之后的 {}'.format(classRoom.name)

			#没有课
			isIdle = not queryExist(overlayedCourse(start,end))
			#没有预约
			isIdle = isIdle and not queryExist(overlayedReservation(start,end,classRoom))

			if isIdle:
				reservation = Reservation(user=g.user, room=classRoom, start=start, end=end)
				db.session.add(reservation)
				db.session.commit()
				break
	else:
		if room is None: return '此时段预约已满'
		else: return '此时段的 {} 预约已满'.format(room.name)

	result = '您已预约 {}'.format(reservation.getDateRoom())
	t1,t2 = datetime.time(hour=8), datetime.time(hour=22, minute=30)
	if not (t1<=reservation.start.time()<=t2 and t1<=reservation.end.time()<=t2):
		result += '\n警告：此时段琴房可能不开'
	return result


@message(patterns.cancellation)
@authenticated
def processCancellation(time, roomName):
	query = Reservation.query.filter_by(user=g.user)
	if roomName is not None:
		query = query.filter_by(room=getRoom(roomName))
	reservations = query.filter(db.and_(Reservation.start<=time, time<Reservation.end))
	resultList = [r.getDateRoom() for r in reservations]
	if len(resultList)==0:
		return '您没有预约{}年{}月{}日{}:{:02}的{}'.format(
				time.year, time.month, time.day,
				time.hour, time.minute,
				'琴房' if roomName is None else roomName)
	reservations.delete()
	db.session.commit()
	return '您已取消{}{}'.format('\n'*(len(resultList)>1), '\n'.join(resultList))


@message(patterns.queryMyself)
@authenticated
def processQueryMyself():
	reservations = (g.user.reservations.filter(datetime.datetime.now()<Reservation.start)
			.order_by(Reservation.start))
	resultList = [r.getDateRoom() for r in reservations]
	if len(resultList)==0:
		return '您目前没有预约'
	return '您的预约:{}{}'.format('\n'*(len(resultList)>1), '\n'.join(resultList))


def queryOccupations(date):
	start, end = toDatetime(date), toDatetime(date+datetime.timedelta(days=1))
	reservations = [dict(
		room = x.room.id,
		start = x.start.time(),
		end = x.end.time(),
		repr = '{:02}:{:02}~{:02}:{:02} {}'.format(x.start.hour, x.start.minute,
			x.end.hour, x.end.minute, x.user.name),
		) for x in overlayedReservation(start, end)]

	courses = [dict(
		room = x.room.id,
		start = x.startTime,
		end = x.endTime,
		repr = '{:02}:{:02}~{:02}:{:02} {}*'.format(x.startTime.hour, x.startTime.minute,
			x.endTime.hour, x.endTime.minute, x.teacher.name)
		) for x in overlayedCourse(start, end)]

	return (reservations, courses)


def formatDate(date):
	return '{}年{}月{}日'.format(date.year, date.month, date.day)


def formatReservation(date, reservations, courses):
	dateRepr = formatDate(date)
	resultList = reservations + courses
	resultList.sort(key=lambda x:(x['room'], x['start'], x['end']))
	resultRepr = '{}：'.format(dateRepr)
	for i,x in enumerate(resultList):
		if i==0 or x['room']!=resultList[i-1]['room']:
			resultRepr += '\n'*(i>0) + '\n[{}]'.format(Room.query.get(x['room']).name)
		resultRepr += '\n{}'.format(x['repr'])
	return resultRepr

@message(patterns.query)
@authenticated
def processQuery(start, end):
	assert start.time() == end.time() == datetime.time()

	if 1 and start.date()==end.date() and (start.month,start.day)==(6,4):
		return randomEmojiLink(emoji='\U0001F1E8\U0001F1F3', link='http://www.xiami.com/song/3598817')

	hasCourse = False
	result = []
	for i in range((end.date() - start.date()).days):
		date = start.date() + datetime.timedelta(days=i)
		reservations, courses = queryOccupations(date)

		if len(reservations) + len(courses) == 0:
			continue

		result.append(formatReservation(date, reservations, courses))
		hasCourse = hasCourse or len(courses) > 0

	if len(result)==0:
		intervalRepr = formatDate(start.date())
		end0 = end.date() - datetime.timedelta(days=1)
		if start.date() != end0:
			intervalRepr += '至' + formatDate(end0)
		return '{}没有预约'.format(intervalRepr)

	if hasCourse:
		result.append('(*) 钢琴课')

	return '\n\n'.join(result)

# 初始化数据库(慎用)
def initDb():
	try: os.remove('db')
	except OSError: pass

	db.create_all()

	#room
	B250 = Room(name='B250')
	B252 = Room(name='B252')
	B253 = Room(name='B253')
	db.session.add(B252)
	db.session.add(B253)

	#legacy db
	legacyName = 'db.legacy'
	try: os.remove(legacyName)
	except OSError: pass
	print('fetching legacy db ...')
	statusCode = os.system('scp hsw@115.159.82.217:/var/www/papuwx/db.sqlite3 {}'.format(legacyName))
	if statusCode != 0:
		raise RuntimeError('error while fetching legacy db')
	conn = sqlite3.connect(legacyName)

	#legacy users
	curs = conn.cursor()
	curs.execute('SELECT id,openid,name FROM users_person')
	users = {}
	for theId, openId, name in curs:
		user = User(openId=openId, name=name)
		users[theId] = user
		db.session.add(user)
	
	#legacy reservations
	curs=conn.cursor()
	curs.execute('SELECT start,end,person_id FROM appointment_appointment')
	practiceRoom, classRoom = Room.query.order_by(Room.id)
	for start, end, personId in curs:
		user = users[personId]
		start = datetime.datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
		end = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M:%S')
		reservation = Reservation(user=user, start=start, end=end, room=practiceRoom)
		db.session.add(reservation)

	conn.close()
	try: os.remove(legacyName)
	except OSError: pass

	refreshCourses()

	#show
	for line in open('performers.txt'):
		performerNames = line.split()
		for performerName in performerNames:
			user = getCreateUser(performerName)
			show = Show(performer=user)
			db.session.add(show)

	db.session.commit()


def refreshCourses():
	B252 = getRoom('B252')
	B250 = getRoom('B250')
	B253 = getRoom('B253')
	Course.query.delete()
	for line in open('courses.txt'):
		weekday, startHour, endHour, teacherName = line.split()
		print(weekday, startHour, endHour, teacherName)
		weekday = '周一 周二 周三 周四 周五 周六 周日'.split().index(weekday)
		startTime = datetime.time(hour=int(startHour))
		endTime = datetime.time(hour=int(endHour))
		startDate = datetime.date(year=2021, month=3, day=1)
		endDate = datetime.date(year=2021, month=7, day=1)
		teacher = getCreateUser(teacherName)
		room = B250
		course = Course(teacher=teacher, room=room, weekday=weekday,
				startDate=startDate, endDate=endDate, startTime=startTime, endTime=endTime)
		db.session.add(course)
		db.session.commit()

def getCreateUser(name):
	print('getting', name)
	user = User.query.filter_by(name=name)
	print(user)
	user = user.first()
	if user is None:
		user = User(name=name)
		db.session.add(user)
		db.session.commit()
	print('got', name, user)
	return user


if __name__=='__main__':

	if len(sys.argv)==2 and sys.argv[1]=='init':
	# 初始化命令的入口
		if input("All data will be deleted. Are you sure? ")=='yes':
			initDb()
			print('done')
		else:
			print('aborted')
	elif len(sys.argv)==2 and sys.argv[1]=='refreshcourses':
	# 刷新钢琴课命令的入口
		if input("Old courses will be deleted. Are you sure? ") in ['Y','y','YES','Yes','yes']:
			refreshCourses()
			print('done')
		else:
			print('aborted')
	else:
	# 启动 Flask
		Manager(app).run()
		# app.run(debug=True, host='::', port=80)
