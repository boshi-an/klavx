#!/usr/bin/python3
# vim: set noet ts=4 sw=4 fileencoding=utf-8:

import re
import datetime

from processor import pattern
from utils import currentDate, toDatetime


def prefix(prefixPat):
	def decorate(entry):
		def newEntry(inputStr):
			prefixMatch = re.match(prefixPat, inputStr)
			if prefixMatch is None: return

			start = prefixMatch.end()
			result = entry(inputStr[start:].strip())
			if result is None:
				raise MyValueError(inputStr[start:])
			return result
		return newEntry
	return decorate


@prefix(r'预约')
@pattern(r'^(?:#(date:date)的?)?\s*\
		   #(time:time1)\s*\
		   #(to)\s*\
		   #(time:time2)\s*\
		   (?:[的\s]#(roomName:roomName))?$')
def reservation(result, date, time1, time2, roomName):
	'返回(开始datetime, 结束datetime)'
	date = date or datetime.date.today()
	if not time1['time']<time2['time']:
		# 如果是“下午三点到五点”（此时time1.hour==15, time2.hour==5）
		# 将其调整为15点到17点
		if time1['section'] is None:
			raise MyValueError(result)
		if time2['time'].hour<12:
			time2['time'] = time2['time'].replace(hour=time2['time'].hour+12)
		if not (time1['time']<time2['time'] and
				time1['section'][0]<=time2['time']<=time1['section'][1]):
			raise MyValueError(result)
	result = (datetime.datetime.combine(date, time1['time']),
			datetime.datetime.combine(date, time2['time']),
			roomName)
	if result[0] < datetime.datetime.now():
		raise ValueError('不能预约过去的时间')
	return result


@prefix(r'取消预约|取消')
@pattern(r'^#(date:date)?的?\s*\
		    #(time:time)\s*\
			(?:#(to)\s*#(time)\s*)?\
			(?:[的\s]#(roomName:roomName))?$')
def cancellation(result, date, time, roomName):
	'即便提供了结束时间，也将其忽略'
	date = date or datetime.date.today()
	return (datetime.datetime.combine(date, time['time']), roomName)


@prefix(r'查询预约|查询')
@pattern(r'^#(date:date)|#(week:week)')
#只匹配前缀，可以有多余后缀，例如“查询明天下午，查询明天的预约，等等
def query(result, date, week):
	if date is not None:
		return (toDatetime(date), toDatetime(date+datetime.timedelta(days=1)))

	return (toDatetime(max(currentDate(), week[0])), toDatetime(week[1]))


@prefix(r'查询我的预约')
@pattern(r'^$')
def queryMyself(result):
	return [] #返回0个参数


@prefix(r'我是')
@pattern(r'^\s*\S+$')
def iAm(result):
	return result.strip()

##########################

@pattern(r'\w+')
def roomName(result):
	return result

@pattern(r'#(relDate:relDate)|#(absDate:absDate)|#(weekDate:weekDate)')
def date(result, relDate, absDate, weekDate):
	'例；今天，大后天，十五号，三月一号，周三，下周日'
	if relDate is not None: return currentDate() + relDate
	if absDate is not None: return absDate
	return weekDate


@pattern(r'#(section:section)?#(hour:hour)#(minute:minute)?')
def time(result, section, hour, minute):
	'例：上午七点，上午十二点半，下午十二点半，下午三点，下午十三点'
	time = datetime.time(hour, minute if minute is not None else 0)
	if section is not None:
		if not section[0]<=time<=section[1] and time.hour<12:
			time = time.replace(hour=time.hour+12)
		if not section[0]<=time<=section[1]:
			raise MyValueError(result)
	return dict(time=time, section=section)


@pattern(r'#(today:today)|#(tomorrow:tomorrow)|#(thremorrow:thremorrow)')
def relDate(result, today, tomorrow, thremorrow):
	if today is not None: return today
	if tomorrow is not None: return tomorrow
	return thremorrow


@pattern(r'(?:#(year:year)?#(month:month))?#(day:day)')
def absDate(result, year, month, day):
	"""
	"某年某月某日"，可以省略年或年月。
	如果有所省略，且自动补全的日期早于当前日期，则试图做最小改动使得结果晚于当前日期。
	例如，如果当前是2016年4月30日，year=None, month=None, day=1，则结果为2016年5月1日；
	如果当前是2016年12月31日，year=None, month=1, day=1，则结果为2017年1月1日。
	"""
	try:
		currentDate0 = currentDate()
		year0 = year if year is not None else currentDate0.year
		month0 = month if month is not None else currentDate0.month
		date = datetime.date(year0, month0, day)

		if date < currentDate0 and month is None:
			if month0 < 12:
				date = date.replace(month=month0+1)
			else:
				date = date.replace(year=year0, month=1)
		if date < currentDate0 and year is None:
			date = date.replace(year=year0+1)
		return date
	except ValueError:
		raise MyValueError(result)


@pattern(r'#(weekCount:weekCount)(?:星期|礼拜|周)')
def week(result, weekCount):
	date = currentDate()
	if weekCount is not None:
		date -= datetime.timedelta(days=date.weekday())
		for i in range(weekCount):
			date += datetime.timedelta(days=7-date.weekday())
	return (date, date + datetime.timedelta(days=7-date.weekday()))


@pattern(r'#(week:week)#(weekNum:weekNum)')
def weekDate(result, week, weekNum):
	"""
	例：下下下周二
	如果没有“下”且weekNum小于当前周内数，则视为下周
	"""
	date = week[0] + datetime.timedelta(days=(weekNum-week[0].weekday()+7)%7)
	if date < currentDate():
		raise MyValueError(result)
	return date


@pattern(r'这|本|下*')
def weekCount(result):
	if len(result) == 0:
		return None
	return result.count('下')


@pattern(r'#(number:number)|[日天]')
def weekNum(result, number):
	'周一到周日分别对应数字0~6'
	if number is None:
		return 6
	if 1<=number<=7:
		return number-1
	raise MyValueError(result)


@pattern(r'#(number:number)年')
def year(result, number):
	'未来十年内之内的年份，例如2016...2025'
	if not 0<=number-currentDate().year<10:
		raise MyValueError(result)
	return number


@pattern(r'#(number:number)月')
def month(result, number):
	'一月...十二月'
	if 1<=number<=12: return number
	raise MyValueError(result)


@pattern(r'#(number:number)(?:日|号)')
def day(result, number):
	'一号...三十一号'
	if 1<=number<=31: return number
	raise MyValueError(result)


@pattern(r'今天?')
def today(result): return datetime.timedelta(days=0)

@pattern(r'明天?')
def tomorrow(result): return datetime.timedelta(days=1)

@pattern(r'大*后天?')
def thremorrow(result): return datetime.timedelta(days=len(result))


@pattern(r'#(sectionMorning:sectionMorning)|#(sectionEvening:sectionEvening)')
def section(result, sectionMorning, sectionEvening):
	return sectionMorning or sectionEvening


@pattern(r'早上?|上午')
def sectionMorning(result):
	"""
	从凌晨到下午一点前都可以算作上午。
	十二点既可以算作上午也可以算作下午。
	"""
	return (datetime.time(0,0,0), datetime.time(12,59,59))


@pattern(r'晚上?|下午|傍晚')
def sectionEvening(result):
	'从十二点到第二天之前算作下午'
	return (datetime.time(12,0,0), datetime.time(23,59,59))


@pattern(r'#(number:number)[点时:：]')
def hour(result, number):
	if not 0<=number<24:
		raise MyValueError(result)
	return number


@pattern(r'#(number:number)分?|#(bigMinute:bigMinute)')
def minute(result, number, bigMinute):
	if bigMinute is not None: return bigMinute
	if not 0<=number<60:
		raise MyValueError(result)
	return number


@pattern(r'#(halfHour:halfHour)|#(quarters:quarters)')
def bigMinute(result, halfHour, quarters):
	return halfHour or quarters

@pattern(r'半')
def halfHour(result): return 30

@pattern(r'#(number:number)刻')
def quarters(result, number):
	'一刻：15，三刻：45'
	if not 1<=number<=3:
		raise MyValueError(result)
	return number*15


@pattern(r'[-~～－—–−到至]')
def to(result):
	return result


@pattern(r'#(arabicNumber:arabicNumber)|#(chineseNumber:chineseNumber)')
def number(result, arabicNumber, chineseNumber):
	if arabicNumber is not None: return arabicNumber
	return chineseNumber

@pattern(r'[0-9]+')
def arabicNumber(result): return int(result)

@pattern(r'[零一二两三四五六七八九十]+')
def chineseNumber(result):
	'解析[零,九十九]内的数字'
	digits = result.split('十')
	if len(digits)>2 or max(len(x) for x in digits)>1:
		raise MyValueError(result)
	if len(digits)==1:
		digits = ['零'] + digits
	digits[0] = digits[0] or '一'
	digits[1] = digits[1] or '零'
	d = {'零':0,'一':1,'二':2,'两':2,'三':3,'四':4,
		 '五':5,'六':6,'七':7,'八':8,'九':9}
	for i,digit in enumerate(digits):
		digits[i] = d[digit]
	return digits[0]*10+digits[1]



class MyValueError(ValueError):
	def __init__(self, msg):
		ValueError.__init__(self, '不能识别"%s"'%msg)


if __name__=='__main__':
	import processor
	import re
	#s = cancellation('取消预约三十号七点半到九点三刻')
	#s = query('查询明天晚上')
	s = week('这周')
	#s = roomName('B252')
	print(s)
	#for k,v in processor.ExtPattern.collection.iteritems():
	#	try: re.compile(v.calcPattern())
	#	except: print k
	#re.compile(processor.ExtPattern.collection['reservation'].calcPattern())
	#s = to('-')
	#s = cancellation('取消今天八点')
	#s = processor.ExtPattern.collection['relDate'].calcPattern()
	#s = re.match(s, '今天')
