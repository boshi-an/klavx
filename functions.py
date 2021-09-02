import datetime
import random

from flask import g

from exception import MyException
from database import Course, Reservation, Room, Registration, User, Message, db

def isEmpty(query) :
	return len(query[:1])==0

def authenticated(func):
	def newFunc(*args, **kwargs):
		user = User.query.filter_by(openId=g.openId).first()
		if user is None:
			raise MyException('抱歉，您还没有登记。请发送 我是xxx')
		g.user = user
		return func(*args, **kwargs)
	return newFunc

def getRoom(roomName):
	room = Room.query.filter_by(name=roomName).first()
	if room is None:
		raise MyException('没有找到 {} 琴房'.format(roomName))
	return room

def overlayedReservation(start, end, room=None) :
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

# 返回一个随机的表情
def randomEmoji() :

	available = [(0x1f31a,0x1f31e), (0x1f646,0x1f64f)]
	pos = random.randrange(sum(x[1]-x[0]+1 for x in available))
	for x in available:
		if pos < x[1]-x[0]+1:
			return chr(x[0]+pos)
		pos -= x[1]-x[0]+1

def vagueRequest() :

	return '嘤嘤嘤，你说的话有点模糊呢，小AI不太理解'

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
				isIdle = isEmpty(overlayedReservation(start, end, practiceRoom))
				if isIdle:
					reservation = Reservation(user=g.user, room=practiceRoom, start=start, end=end)
					db.session.add(reservation)
					db.session.commit()
					roomFound = True
					break
		if roomFound: break

		if room is None or room==classRoom:
			#在本学期有课还没上完的时候，只有老师可以预约两天之后的classRoom
			if not ((not isEmpty(g.user.courses) #是老师
				or (start.date()-datetime.datetime.now().date()).days <= 2)):
				return '抱歉，只有教课的老师可以预约超过 2 天之后的 {}'.format(classRoom.name)

			#没有课
			isIdle = isEmpty(overlayedCourse(start,end))
			#没有预约
			isIdle = isIdle and isEmpty(overlayedReservation(start,end,classRoom))

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
def processCancel(begin, end, location):
	print(begin, end, location)
	query = Reservation.query.filter_by(user=g.user)
	if location is not None:
		query = query.filter_by(room=getRoom(location))
	if begin is not None and end is not None :
		query = query.filter(db.and_(begin<=Reservation.start, Reservation.end<=end))
	elif begin is not None and end is None :
		query = query.filter(db.and_(Reservation.start<=begin, Reservation.end>=begin))
	resultList = [r.getDateRoom() for r in query]
	if len(resultList)==0:
		if begin is not None and end is not None :
			return '您没有{}到{} '.format(begin, end, location) + (location if location is not None else '') + '的预约'
		elif begin is not None and end is None :
			return '您没有包含{} '.format(begin, location) + (location if location is not None else '') + '的预约'
	query.delete()
	db.session.commit()
	return '您已取消{}{}'.format('\n'*(len(resultList)>1), '\n'.join(resultList))

@authenticated
def processQuery() :
	pass