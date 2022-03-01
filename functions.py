import datetime
import random
from re import match
import utils

from flask import g, current_app

from exception import MyException
from database import Course, Reservation, Room, Registration, User, Message, Logs, db


def authenticated(func) :
	def newFunc(*args, **kwargs) :
		user = User.query.filter_by(openId=g.openId).first()
		if user is None :
			raise MyException('抱歉，您还没有登记。请发送 我是xxx')
		g.user = user
		return func(*args, **kwargs)
	return newFunc

def isAdmin(func) :
	def newFunc(*args, **kwargs) :
		user = User.query.filter(db.and_(User.openId==g.openId, User.administrator==1)).first()
		if user is None :
			raise MyException('只有管理员可以使用此命令')
		g.user = user
		return func(*args, **kwargs)
	return newFunc

def getRoom(roomName):
	if roomName is None :
		return None
	room = Room.query.filter_by(name=roomName).first()
	if room is None :
		raise MyException('没有找到 {} 琴房'.format(roomName))
	return room


def overlayedReservation(start, end, room=None) :
	query = Reservation.query if room is None else room.reservations
	if end is not None :
		return query.filter(db.or_(
			db.and_(Reservation.start<start, Reservation.end>start), # ( [ )
			db.and_(Reservation.start>=start, Reservation.start<end)) # [ ( ]
		)
	else :
		return query.filter(
			db.and_(Reservation.start<=start, Reservation.end>=start)
		)

def overlayedCourse(start, end, room=None):
	query = Course.query if room is None else room.courses
	if end is not None :
		end -= datetime.timedelta(microseconds=1)
		assert start.date() == end.date()

		return (query.filter_by(weekday=start.weekday())
				.filter(db.and_(Course.startDate<=start.date(),
					Course.endDate>=start.date()))
				.filter(db.or_(
					db.and_(Course.startTime<start.time(), Course.endTime>start.time()),
					db.and_(Course.startTime>=start.time(), Course.startTime<=end.time()))))
	else :
		return (query.filter_by(weekday=start.weekday())
				.filter(db.and_(Course.startDate<=start.date(),
					Course.endDate>=start.date(), Course.startTime<=start.time(), Course.endTime>=start.time())))

def queryOccupations(start, end, room):
	reservations = [dict(
		room = x.room.id,
		start = x.start.time(),
		end = x.end.time(),
		repr = '{:02}:{:02}~{:02}:{:02} {}'.format(x.start.hour, x.start.minute,
			x.end.hour, x.end.minute, x.user.name),
		) for x in overlayedReservation(start, end, room)]

	courses = [dict(
		room = x.room.id,
		start = x.startTime,
		end = x.endTime,
		repr = '{:02}:{:02}~{:02}:{:02} {} (*)'.format(x.startTime.hour, x.startTime.minute,
			x.endTime.hour, x.endTime.minute, x.teacher.name)
		) for x in overlayedCourse(start, end, room)]

	return (reservations, courses)

def formatOccupation(date, reservations, courses):
	dateRepr = utils.formatDate(date)
	resultList = reservations + courses
	resultList.sort(key=lambda x:(x['room'], x['start'], x['end']))
	resultRepr = '{}：'.format(dateRepr)
	for i,x in enumerate(resultList):
		if i==0 or x['room']!=resultList[i-1]['room']:
			resultRepr += '\n'*(i>0) + '\n[{}]'.format(Room.query.get(x['room']).name)
		resultRepr += '\n{}'.format(x['repr'])
	return resultRepr

# 返回一个随机的表情
def randomEmoji() :

	available = [(0x1f31a,0x1f31e), (0x1f646,0x1f64f)]
	pos = random.randrange(sum(x[1]-x[0]+1 for x in available))
	for x in available:
		if pos < x[1]-x[0]+1:
			return chr(x[0]+pos)
		pos -= x[1]-x[0]+1

def vagueRequest() :

	return '嘤嘤嘤，你说的话有点模糊呢，小AI不太理解。输入“帮助”学习如何跟小AI交流'

def processIam(name) :
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

@authenticated
def processReservation(start, end, roomName):

	curUser = User.query.filter_by(openId=g.openId).all()

	utils.writeLog('Reservation', str(start)+', '+str(end)+', '+str(roomName)+', '+str(curUser), '1;32;40')

	if len(curUser) == 0 or curUser[0].authorized != 1 :
		return '抱歉，只有经过认证的演奏部成员可以预约'
	if len(curUser) > 1 :
		return '发现重名openID，请联系技术部负责人！'


	result = ''

	if end is None :
		result += '由于您没有给定结束时间，默认您的预约时常为1小时\n'
		end = start + datetime.timedelta(hours=1)
	# ???
	if (start.month,start.day)==(6,4):
		return randomEmoji()

	# 活跃预约数不超过2
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
				isIdle = utils.isEmpty(overlayedReservation(start, end, practiceRoom))
				if isIdle:
					reservation = Reservation(user=g.user, room=practiceRoom, start=start, end=end)
					db.session.add(reservation)
					db.session.commit()
					roomFound = True
					break
		if roomFound: break

		if room is None or room==classRoom:
			#在本学期有课还没上完的时候，只有老师可以预约两天之后的classRoom
			if not ((not utils.isEmpty(g.user.courses) #是老师
				or (start.date()-datetime.datetime.now().date()).days <= 2)):
				return '抱歉，只有教课的老师可以预约超过 2 天之后的 {}'.format(classRoom.name)

			#没有课
			isIdle = utils.isEmpty(overlayedCourse(start,end))
			#没有预约
			isIdle = isIdle and utils.isEmpty(overlayedReservation(start,end,classRoom))

			if isIdle:
				reservation = Reservation(user=g.user, room=classRoom, start=start, end=end)
				db.session.add(reservation)
				db.session.commit()
				break
	else:
		if room is None:
			return '此时段预约已满'
		else:
			return '此时段的 {} 预约已满'.format(room.name)

	result += '您已预约 {}'.format(reservation.getDateRoom())
	t1,t2 = datetime.time(hour=8), datetime.time(hour=22, minute=30)
	if not (t1<=reservation.start.time()<=t2 and t1<=reservation.end.time()<=t2):
		result += '\n警告：此时段琴房可能不开'
	return result

@authenticated
def processCancel(start, end, roomName):

	utils.writeLog('Cancellation', str(start)+', '+str(end)+', '+str(roomName), '1;32;40')

	query = Reservation.query.filter_by(user=g.user)
	
	# 如果开始时间只是一个日期，并且没有结束时间，意味着取消这一天的预约
	if type(start) is datetime.date and end is None :
		start = utils.toDatetime(start)
		end = start + datetime.timedelta(days=1)

	# 如果开始结束都是一个日期，意味着取消这几天的预约
	if type(start) is datetime.date and type(end) is datetime.date :
		start = utils.toDatetime(start)
		end = utils.toDatetime(end + datetime.timedelta(days=1))

	# 如果没有开始日期，意味着取消当前时间之后的预约
	if start is None :
		start = datetime.datetime.now()
		end = start + datetime.timedelta(days=365)
	
	if roomName is not None:
		query = query.filter_by(room=getRoom(roomName))
	if start is not None and end is not None :
		query = query.filter(db.and_(start<=Reservation.start, Reservation.end<=end))
	elif start is not None and end is None :
		query = query.filter(db.and_(Reservation.start<=start, Reservation.end>=start))
	resultList = [r.getDateRoom() for r in query]
	if len(resultList)==0:
		if start is not None and end is not None :
			return '您没有{}到{} '.format(start, end, roomName) + (roomName if roomName is not None else '') + '的预约'
		elif start is not None and end is None :
			return '您没有包含{} '.format(start) + (roomName if roomName is not None else '') + '的预约'
		elif roomName is not None :
			 return '您没有{} '.format(roomName) + '的预约'
	query.delete()
	db.session.commit()
	return '您已取消{}{}'.format('\n'*(len(resultList)>1), '\n'.join(resultList))

@authenticated
def processQuery(start, end, roomName, userId = None) :

	utils.writeLog('Query', str(start)+', '+str(end)+', '+str(roomName)+', '+str(userId), '1;32;40')
	matches = []
	timeRepr = ''
	hasCourse = False

	if end is not None and (end.date() - start.date()).days > 33 :
		return '您查询的时间区间过长'

	# 给定时间区间
	if start is not None and end is not None :
		for i in range((end.date() - start.date()).days+1) :
			date = (start + datetime.timedelta(days=i)).date()
			tmpReserve, tmpCourses = queryOccupations(utils.toDatetime(date), utils.toDatetime(date+datetime.timedelta(days=1)), getRoom(roomName))
			if len(tmpReserve) + len(tmpCourses) == 0 :
				continue
			matches.append(formatOccupation(date, tmpReserve, tmpCourses))
			hasCourse = hasCourse or (len(tmpCourses)>0)
		timeRepr = utils.formatDate(start) + '至' + utils.formatDate(end)
	# 给定时间点
	elif start is not None and end is None :
		tmpReserve, tmpCourses = queryOccupations(start, None, getRoom(roomName))
		hasCourse = len(tmpCourses)>0
		timeRepr = utils.formatDatetime(start)
	# 给定用户名
	elif userId is not None :
		start = datetime.datetime.now()
		thisUser = User.query.filter(User.openId == userId).first()
		allReserve = thisUser.reservations.filter(db.and_(Reservation.start>=start)).all()
		for reserve in allReserve :
			matches.append(formatOccupation(reserve.start, *queryOccupations(reserve.start, reserve.end, reserve.room)))
		timeRepr = '你：'

	# 没有给定时间，默认当前时间
	elif start is None and end is None :
		start = datetime.datetime.now()
		tmpReserve, tmpCourses = queryOccupations(start, None, getRoom(roomName))
		hasCourse = len(tmpCourses)>0
		timeRepr = utils.formatDatetime(start)


	if roomName is not None :
		timeRepr += '的' + roomName

	if len(matches) == 0:
		return '{}没有预约'.format(timeRepr)

	if hasCourse :
		matches.append('(*)钢琴课')

	return timeRepr+'\n\n'+'\n\n'.join(matches)

# 从User表中取出某一个名字对应的用户项，如果不存在，则新建一个用户项
def getCreateUser(name):
	print('getting', name)
	user = User.query.filter_by(name=name)
	user = user.first()
	if user is None:
		utils.writeLog('CreateUser', name, '1;33;40')
		user = User(name=name)
		db.session.add(user)
		db.session.commit()
	print('got', name, user)
	return user

def refreshCourses(fileName):
	if datetime.datetime.now().month < 8 :
		startDate = datetime.date(year=2021, month=3, day=1)
		endDate = datetime.date(year=2022, month=7, day=1)
	else :
		startDate = datetime.date(year=2021, month=9, day=1)
		endDate = datetime.date(year=2022, month=1, day=1)
	
	B252 = getRoom('B252')
	B250 = getRoom('B250')
	B253 = getRoom('B253')
	Course.query.delete()
	for line in open(fileName):
		weekday, startHour, endHour, teacherName = line.split()
		print(weekday, startHour, endHour, teacherName)
		weekday = '周一 周二 周三 周四 周五 周六 周日'.split().index(weekday)
		startTime = datetime.time(hour=int(startHour))
		endTime = datetime.time(hour=int(endHour))
		teacher = getCreateUser(teacherName)
		room = B250
		course = Course(teacher=teacher, room=room, weekday=weekday,
				startDate=startDate, endDate=endDate, startTime=startTime, endTime=endTime)
		db.session.add(course)
		db.session.commit()

def authorizeUsers(name) :
	user = getCreateUser(name)
	print('authorizing', user)
	user.authorized = 1
	db.session.commit()

def makeAdmin(name) :
	user = getCreateUser(name)
	print('authorizing', user)
	user.administrator = 1
	db.session.commit()

def about() :

	return '这里是北京大学钢琴社,欢迎关注钢琴社公众号\n（づ￣3￣）づ╭❤～\n\n\
		输入“我是xxx”可以注册新用户，让小AI知道你是谁\n\n\
		你还可以在这里留言（后台有人定期回复）\n\n\
		输入“帮助”可以获得操作指南\n\n\
		输入“常见问题”了解更多'

def frequentQuestions() :

	return 'Q:钢琴课下个学期开吗？什么时候报名？\n\
			A:每个学期都开的，社团招新的时候报名\n\n\
			Q:演奏部什么时候招新？\n\
			A:每个学期社团招新时都可以报名参加面试进入演奏部\n\n\
			Q:学校里有地方练琴吗？\n\
			A:北京大学没有提供公共琴房，新太阳学生中心地下的琴房仅供演奏部成员排练使用'

def easterEgg() :

	return '今天你练琴了吗' + randomEmoji()

def help() :

	return '你可以在这里留言（后台有人定期回复），在这里预约琴房（仅供演奏部排练用哦，平时练琴不需要也不应该预约），也可以查询预约情况\n\n\
		预约的格式为：“预约+[时间起点]+到/至+[时间终点]+琴房名”，后面两项可以省略\n\n\
		查询的格式为：“查询+[时间起点]+到/至+[时间终点]+琴房名”，后面两项可以省略\n\n\
		注册的格式为：“我是xxx”'

@isAdmin
def checkLog() :

	current_app.adminCode = random.randint(1,1000000000)
	return 'http://82.157.114.38/klavx/admin/?code='+str(current_app.adminCode)

def showDatabase(dbName) :

	p = dbName.query.all()
	for i in p :
		print(i)