import datetime
from lxml import etree

# toEtree的作用是将传入的参数d转换为一个数据包结构并返回，默认转换为'xml'类型
# 如果d是列表/元组/字典，对d中的每一个键值对，递归调用toEtree
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

def printDict(name, d) :
	print(name, ":")
	for key,val in d.items() :
		print('\t',key,":",str(val).replace('\n','\n\t\t'))
	print('\n')

def packTexttoLXML(text, ToUserName, FromUserName, CreateTime) :
	
	reply = toEtree(dict(FromUserName=ToUserName, ToUserName=FromUserName, CreateTime=CreateTime))
	
	# 将replyDict中的数据加入ElementTree
	replyDict = dict(MsgType='text', Content=text)
	for k,v in replyDict.items():
		reply.append(toEtree(v, name=k))
	
	return reply

def isEmpty(query) :
	return len(query[:1])==0

def toDatetime(date) :
	return datetime.datetime.combine(date, datetime.time(0, 0, 0, 0))

def formatDate(date) :
	return '{}年{}月{}日'.format(date.year, date.month, date.day)

def formatDatetime(dtime) :
	return '{}年{}月{}日{}:{:02}'.format(dtime.year, dtime.month, dtime.day, dtime.hour, dtime.minute)