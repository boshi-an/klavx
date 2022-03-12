
import datetime
import re

from flask import current_app, g

import exception
import utils


def givenPattern(pat) :
	def wrapped(string) :
		return pat.match(string)
	return wrapped

def givenRegx(reg) :
	def wrapped(string) :
		res = reg.search(string)
		if res == None :
			return ((0, 0), None)
		return (res.span(), res.group())
	return wrapped

# We define any pattern as several parallel possible sub_pattern sequence:
# pattern = [[sub1, sub2, sub3], [sub1, sub2, sub3]]
# when a pattern matches a string, if and only if, one of the sequence is matched

class Pattern :

	def __init__(self) :

		self.subPatterns = []
		self.subResults = []
		self.combiners = []
		
	# I used wrapper to view patterns and regxprs the same way
	# pattern(string) = ((l,r), (res1, res2, ...))
	def appendSubPatternSeq(self, subpattern, combiner) :

		wrappedSubPattern = []
		for item in subpattern :
			if type(item) == Pattern :
				wrappedSubPattern.append(givenPattern(item))
			else :
				item = re.compile(item)
				wrappedSubPattern.append(givenRegx(item))
		self.subPatterns.append(wrappedSubPattern)
		self.combiners.append(combiner)
	
	# match trys every possible pattern sequence to match the given string
	# when one is fit, just return
	def match(self, string) :	# can search on <Pattern> or <re.Match_Object>
		
		for sequence,combiner in zip(self.subPatterns,self.combiners) :
			curStr = string
			curRes = []
			curLen = 0
			for sub in sequence :
				res = sub(curStr)
				if res == None :
					break
				curRes.append(res[1])
				curLen += res[0][1]
				curStr = curStr[res[0][1]:]
			else :
				curSum = combiner(*curRes)
				if curSum != None :
					return ((0, curLen), curSum)
		return None

# TextInterpreter can interpret a string
# pattern and functions are given to the interpreter in pairs
# when only one pattern matches the given string
# the interpreter calls the correspoding function
class TextInterpreter :

	# when there are 0 or more than 1 matches
	# call function whenNone and whenMultiple 
	def __init__(self) :

		self.patternFuncSeq = []
		self.whenNone = None
		self.whenMultiple = None
		pass

	def registerNoneFunction(self, func) :

		self.whenNone = func

	def registerMultipleFunction(self, func) :

		self.whenMultiple = func

	def registerPattern(self, pat, recall) :

		self.patternFuncSeq.append((pat, recall))
	
	# doing interpretation and calling corresponding functions
	def doInterprete(self, string) :

		utils.writeLog('Interpret', string, '1;32;40')

		successNum = 0
		funcParaPair = None
		for pattern,func in self.patternFuncSeq :
			try :
				tmp = pattern.match(string)
			except ValueError as e:
				utils.writeLog('Error', 'Value error occured!', '1;31;40')
				return str(e)
			except exception.MyException as e:
				utils.writeLog('Error', str(e), '1;31;40')
				return str(e)
			except OverflowError as e:
				utils.writeLog('Error', str(e), '1;31;40')
				return str(e)
			if tmp != None :
				_,res = tmp
				funcParaPair = (func, res)
				successNum += 1
		if successNum == 0 :
			utils.writeLog('Warning', 'Can\'t understand!', '1;34;40')
			if self.whenNone != None :
				return self.whenNone()
			else :
				return "No interpretation found!"
		elif successNum >= 2 :
			utils.writeLog('Warning', 'Multiple answers!', '1;34;40')
			if self.whenMultiple != None :
				return self.whenMultiple()
			else :
				return "Multiple interpretation found!"
		else :
			utils.writeLog('InterpretResult', str(funcParaPair[1]), '1;34;40')
			try:
				result = funcParaPair[0](*funcParaPair[1])
			except exception.MyException as e :
				utils.writeLog('Error', str(e), '1;31;40')
				return str(e)
			return result

pReserve = Pattern()
pCancel = Pattern()
pQuery = Pattern()
pIam = Pattern()
pTime = Pattern()
pDate = Pattern()
pClock = Pattern()
pNumber = Pattern()
pLocation = Pattern()
pNumber_adj = Pattern()	# numbers that have no preceeding letters
pSparseTime = Pattern()
pEasterEgg = Pattern()
pCheckLog = Pattern()
pFrequent = Pattern()
pAbout = Pattern()
pHelp = Pattern()

def initPatterns() :

	def chineseNumber(s) :
		return '零一二三四五六七八九十'.index(s)
	
	def readChinese(s) :
		
		if len(s)==1 and s[0] in ['日','天'] :
			return 7
		elif s.isdigit() :
			return int(s)
		else :#是中文
			ret = 0
			t = [chineseNumber(x) for x in s]
			if len(t) == 1 :
				return t[0]
			elif len(t) == 2 :
				if t[0] == 10 :
					return t[1]+10
				else :
					if t[1] != 10 :
						raise exception.MyException('Number '+s+' interpretation error!')
					return t[0]*10
			else :
				if t[1] != 10 or len(s) != 3:
						raise exception.MyException('Number '+s+' interpretation error!')
				return t[0]*10 + t[2]

	def nextMonday() :
		for i in range(1, 10) :
			day = datetime.date.today() + datetime.timedelta(days=i)
			if day.weekday() == 0 :
				return day
		raise exception.MyException("No next monday found!!!")
	
	def haveNone(*arg) :
		for a in arg :
			if a==None :
				return True
		return False

	# Defining numbers
	pNumber.appendSubPatternSeq(
		[r'[零一二三四五六七八九十0-9]+'],
		lambda x : None if x==None else (readChinese(x),)
	)
	pNumber_adj.appendSubPatternSeq(
		[r'^[零一二三四五六七八九十0-9]+'],
		lambda x : None if x==None else (readChinese(x),)
	)

	# Defining date
	pDate.appendSubPatternSeq(
		[r'今天|今日'],
		lambda x : None if x==None else (datetime.date.today(),)
	)
	pDate.appendSubPatternSeq(
		[r'明天'],
		lambda x : None if x==None else (datetime.date.today() + datetime.timedelta(days=1),)
	)
	pDate.appendSubPatternSeq(
		[r'大*后天'],
		lambda x : None if x==None else (datetime.date.today() + datetime.timedelta(days=1)*len(x),)
	)
	pDate.appendSubPatternSeq(
		[r'下*个?(周|星期)', pNumber_adj],
		lambda x,y : None if haveNone(x,y) else (nextMonday() + datetime.timedelta(days=y[0]%7+x.count('下')*7-8),)
	)
	pDate.appendSubPatternSeq(
		[r'下*个?(周日|星期日|星期天)'],
		lambda x : None if haveNone(x) else (nextMonday() + datetime.timedelta(days=7+x.count('下')*7-8),)
	)
	pDate.appendSubPatternSeq(
		[pNumber, r'^月', pNumber_adj, r'^日*|^号*'],
		lambda x,_1,y,_2 : None if haveNone(x,_1,y,_2) else (datetime.date.today().replace(month=x[0], day=y[0]),)
	)
	pDate.appendSubPatternSeq(
		[pNumber, r'^\.', pNumber_adj, r'^\.', pNumber_adj, r'[ ]|$'],
		lambda x,_1,y,_2,z,_3 : None if haveNone(x,_1,y,_2,z,_3) else (datetime.date.today().replace(year=x[0], month=y[0], day=z[0]),)
	)
	pDate.appendSubPatternSeq(
		[pNumber, r'^\.', pNumber_adj, r'[ ]|$'],
		lambda x,_1,y,_2 : None if haveNone(x,_1,y,_2) else (datetime.date.today().replace(month=x[0], day=y[0]),)
	)

	# Defining clock
	pSparseTime.appendSubPatternSeq(
		[r'上午|早上*'],
		lambda x : None if x==None else ('AM',)
	)
	pSparseTime.appendSubPatternSeq(
		[r'下午|晚上*'],
		lambda x : None if x==None else ('PM',)
	)

	# Defining clock
	pClock.appendSubPatternSeq(
		[pNumber, r'^\:|^：', pNumber_adj, r'am|pm|AM|PM|Am|Pm'],
		lambda x,_,y,z : None if haveNone(x,_,y,z) else (datetime.datetime.strptime(str(x[0])+':'+str(y[0])+' '+z.lower(), '%I:%M %p').time(), )
	)
	pClock.appendSubPatternSeq(
		[pNumber, r'\:|点|时|^：', pNumber_adj],
		lambda y,_,z : None if haveNone(y,_,z) else (datetime.datetime.strptime(str(y[0])+':'+str(z[0]), '%H:%M').time(),)
	)
	pClock.appendSubPatternSeq(
		[pNumber, r'^点半'],
		lambda y,z : None if haveNone(y,z) else (datetime.datetime.strptime(str(y[0])+':'+str(30), '%H:%M').time(), )
	)
	pClock.appendSubPatternSeq(
		[pNumber, r'^点|^时'],
		lambda y,z : None if haveNone(y,z) else (datetime.datetime.strptime(str(y[0])+':'+str(00), '%H:%M').time(), )
	)

	# Defining location
	pLocation.appendSubPatternSeq(
		[r'B|b', pNumber_adj],
		lambda x,y : None if haveNone(x,y) else ('B'+str(y[0]),)
	)
	pLocation.appendSubPatternSeq(
		[pNumber],
		lambda x : None if x==None else ('B'+str(x[0]),)
	)

	# Defining time
	# time = begin to end
	def moveTime(clock, sparse) :
		clock = clock.replace(hour=clock.hour%12)
		if sparse=='PM' :
			clock = clock.replace(hour=clock.hour+12)
		return clock
	pTime.appendSubPatternSeq(
		[pDate, pSparseTime, pClock, r'到|至|\-|\~|～|-|——', pDate, pSparseTime, pClock],
		lambda x1,y1,z1,_,x2,y2,z2 : None if haveNone(x1,y1,z1,_,x2,y2,z2) else (datetime.datetime.combine(*x1,moveTime(*z1,*y1)), datetime.datetime.combine(*x2,moveTime(*z2,*y2)))
	)
	pTime.appendSubPatternSeq(
		[pDate, pClock, r'到|至|\-|\~|～|-|——', pDate, pClock],
		lambda x1,z1,_,x2,z2 : None if haveNone(x1,z1,_,x2,z2) else (datetime.datetime.combine(*x1,*z1), datetime.datetime.combine(*x2,*z2))
	)
	pTime.appendSubPatternSeq(
		[pDate, pSparseTime, pClock, r'到|至|\-|\~|～|-|——', pSparseTime, pClock],
		lambda x,y1,z1,_,y2,z2 : None if haveNone(x,y1,z1,_,y2,z2) else (datetime.datetime.combine(*x,moveTime(*z1,*y1)), datetime.datetime.combine(*x,moveTime(*z2,*y2)))
	)
	pTime.appendSubPatternSeq(
		[pDate, pSparseTime, pClock, r'到|至|\-|\~|～|-|——',  pClock],
		lambda x,y,z1,_,z2 : None if haveNone(x,y,z1,_,z2) else (datetime.datetime.combine(*x,moveTime(*z1,*y)), datetime.datetime.combine(*x,moveTime(*z2,*y)))
	)
	pTime.appendSubPatternSeq(
		[pDate, pSparseTime, pClock],
		lambda x,y,z : None if haveNone(x,y,z) else (datetime.datetime.combine(*x,moveTime(*z,*y)), None)
	)
	pTime.appendSubPatternSeq(
		[pDate, pClock, r'到|至|\-|\~|～|-|——', pClock],
		lambda x,y,_,z : None if haveNone(x,y,_,z) else (datetime.datetime.combine(*x,*y), datetime.datetime.combine(*x,*z))
	)
	pTime.appendSubPatternSeq(
		[pDate, pClock],
		lambda x,y : None if haveNone(x,y) else (datetime.datetime.combine(*x,*y), None)
	)

	# Defining reserve
	# reserve = when and where
	pReserve.appendSubPatternSeq(
		['^预约', pTime, pLocation],
		lambda x,y,z : None if haveNone(x,y,z) else (*y, *z)
	)
	pReserve.appendSubPatternSeq(
		['^预约', pTime],
		lambda x,y : None if haveNone(x,y) else (*y, None)
	)

	# Defining Query
	# query = when and where
	pQuery.appendSubPatternSeq(
		['^查询', pTime, pLocation],
		lambda x,y,z : None if haveNone(x,y,z) else (*y, *z)
	)
	pQuery.appendSubPatternSeq(
		['^查询', pTime],
		lambda x,y : None if haveNone(x,y) else (*y, None)
	)
	pQuery.appendSubPatternSeq(
		['^查询', pDate, r'到|至|-|\~|～', pDate, pLocation],
		lambda _,x,__,y,z : None if haveNone(_,x,__,y,z) else (utils.toDatetime(*x), utils.toDatetime(*y), *z)
	)
	pQuery.appendSubPatternSeq(
		['^查询', pDate, r'到|至|-|\~|～', pDate],
		lambda _,x,__,y : None if haveNone(_,x,__,y) else (utils.toDatetime(*x), utils.toDatetime(*y), None)
	)
	pQuery.appendSubPatternSeq(
		['^查询', pDate, pLocation],
		lambda x,y,z : None if haveNone(x,y,z) else (utils.toDatetime(*y), utils.toDatetime(*y)+datetime.timedelta(days=1)-datetime
		.timedelta(seconds=1), *z)
	)
	pQuery.appendSubPatternSeq(
		['^查询', pDate],
		lambda x,y : None if haveNone(x,y) else (utils.toDatetime(*y), utils.toDatetime(*y)+datetime.timedelta(days=1)-datetime
		.timedelta(seconds=1), None)
	)
	pQuery.appendSubPatternSeq(
		['^查询', pLocation],
		lambda x,y : None if haveNone(x,y) else (None, None, *y)
	)
	pQuery.appendSubPatternSeq(
		['^查询本周|^查询这周'],
		lambda x : None if x==None else (utils.toDatetime(nextMonday())-datetime.timedelta(days=7), utils.toDatetime(nextMonday()), None)
	)
	pQuery.appendSubPatternSeq(
		['^查询下*周'],
		lambda x : None if x==None else (utils.toDatetime(nextMonday())+datetime.timedelta(days=7*(len(x)-4)), utils.toDatetime(nextMonday())+datetime.timedelta(days=7*(len(x)-3)), None)
	)
	pQuery.appendSubPatternSeq(
		['^查询我'],
		lambda x : None if x==None else (None, None, None, g.openId)
	)
	pQuery.appendSubPatternSeq(
		['^查询$'],
		lambda x : None if x==None else (None, None, None)
	)

	# Defining cancellation
	pCancel.appendSubPatternSeq(
		['^取消', pTime, pLocation],
		lambda _,x,y : None if haveNone(_,x,y) else (*x, *y)
	)
	pCancel.appendSubPatternSeq(
		['^取消', pTime],
		lambda _,x : None if haveNone(_,x) else (*x, None)
	)
	pCancel.appendSubPatternSeq(
		['^取消', pDate, '到', pDate],
		lambda _,x,__,y : None if haveNone(_,x,__,y) else (*x, *y, None)
	)
	pCancel.appendSubPatternSeq(
		['^取消', pDate, pClock],
		lambda _,x,y : None if haveNone(_,x,y) else (datetime.datetime.combine(*x, *y), None, None)
	)
	pCancel.appendSubPatternSeq(
		['^取消', pDate],
		lambda _,x : None if haveNone(_,x) else (*x, None, None)
	)
	pCancel.appendSubPatternSeq(
		['^取消', pLocation],
		lambda _,x : None if haveNone(_,x) else (None, None, *x)
	)

	# Defining Frequently Asked Questions
	pFrequent.appendSubPatternSeq(
		['^常见问题'],
		lambda x : None if x==None else []
	)

	# Defining I am
	pIam.appendSubPatternSeq(
		['^我是', '.*'],
		lambda x,y : None if haveNone(x,y) else (y,)
	)

	# Defining a lot of things
	pAbout.appendSubPatternSeq(
		['^关于|^你是|^你好|^hello|^Hello|^Hi|^hi'],
		lambda x : None if x==None else []
	)
	pEasterEgg.appendSubPatternSeq(
		['^彩蛋|^练琴'],
		lambda x : None if x==None else []
	)
	pHelp.appendSubPatternSeq(
		['^帮助|^help|^Help|^HELP'],
		lambda x : None if x==None else []
	)
	pCheckLog.appendSubPatternSeq(
		['^查看日志$|^查看后台$'],
		lambda x : None if x==None else []
	)

	return
	print('下面一长串是测试代码，如果其中有一行为None请小心')
	print(pDate.match('大后天'))
	print(pNumber.match('1982'))
	print(pNumber.match('三十'))
	print(pDate.match('下个周日'))
	print(pDate.match('星期一'))
	print(pDate.match('9月8号'))
	print(pDate.match('2010.9.9'))
	print(pDate.match('12.2'))
	print(pClock.match('下午九点三十'))
	print(pClock.match('19:30'))
	print(pClock.match('早上8:00'))
	print(pClock.match('6:30pm'))
	print(pClock.match('早上八点半'))
	print(pClock.match('晚八点'))
	print(pTime.match('今天早上八点到晚上八点'))
	print(pLocation.match('252'))
	print(pLocation.match('B252'))
	print(pReserve.match('预约2021.9.1 8:40am到晚上七点半的B252'))
	print(pReserve.match('预约明天下午8:00到九点半'))
	print(pQuery.match('查询'))
	print(pQuery.match('查询252'))
	print(pQuery.match('查询明天'))
	print(pQuery.match('查询2020.6.4 252'))
	print(pIam.match('我是李云迪'))
	pass

if __name__ == '__main__' :

	initPatterns()

	'''
	def m1(para) :
		print("pattern1 matched!")
		print(para)
	
	def m2(para) :
		print("pattern2 matched!")
		print(para)
	
	inter = TextInterpreter()
	
	pat1 = Pattern()
	pat1.appendSubPatternSeq([r'[0-9]+', r'\+', r'[0-9]+'], lambda a,b,c:None if a==None or b==None else (int(a)+int(c),))
	inter.registerPattern(pat1, m1)
	inter.doInterprete(input())
	'''
	pass
