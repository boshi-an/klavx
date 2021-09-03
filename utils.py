import datetime

def printDict(name, d) :
	print(name, ":")
	for key,val in d.items() :
		print('\t',key,":",str(val).replace('\n','\n\t\t'))
	print('\n')

def isEmpty(query) :
	return len(query[:1])==0

def toDatetime(date) :
	return datetime.datetime.combine(date, datetime.time(0, 0, 0, 0))

def formatDate(date) :
	return '{}年{}月{}日'.format(date.year, date.month, date.day)

def formatDatetime(dtime) :
	return '{}年{}月{}日{}:{:02}'.format(dtime.year, dtime.month, dtime.day, dtime.hour, dtime.minute)