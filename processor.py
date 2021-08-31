# vim: set noet ts=4 sw=4 fileencoding=utf-8:

import re

dependsRev = {}


def escape(s):
	if isinstance(s, int):
		return '1'*s
	return s.replace('_', '__')


class ExtPattern:
	rootName = 'root'
	collection = {}

	def __init__(self, patternList, func, depends):
		if func.__name__ in ExtPattern.collection:
			raise ValueError('multiple defintion of %s' %func.__name__)

		self.patternList = patternList
		self.func = func
		self.depends = depends
		ExtPattern.collection[func.__name__] = self

	def calcPattern(self, myName=None):
		prefix = myName+'_' if myName else ExtPattern.rootName
		patternList0 = [x[1].calcPattern(prefix+escape(x[0])) if isinstance(x,tuple) else x
						for x in self.patternList]
		pattern = ''.join(patternList0)
		return r'(?P<%s>%s)'%(myName,pattern) if myName else pattern

	def wrap(self, matchObj, prefix=None):
		matchStr = matchObj.group(prefix) if prefix else matchObj.group()
		if matchStr is None: return

		prefix = prefix+'_' if prefix else ExtPattern.rootName
		args = {}
		for piece in self.patternList:
			if isinstance(piece, tuple):
				name, child = piece
				arg = child.wrap(matchObj, prefix+escape(name))
				if not isinstance(name, int):
					args[name] = arg
		return self.func(matchStr, **args)

	def resolvable(self):
		return len(self.depends)==0

	def resolve(self):
		if not self.resolvable(): return

		for i,piece in enumerate(self.patternList):
			if isinstance(piece, tuple):
				name, child = piece
				self.patternList[i] = (name, ExtPattern.collection[child])

		myName = self.func.__name__
		if myName not in dependsRev: return

		for name in dependsRev[myName]:
			extPattern = ExtPattern.collection[name]
			extPattern.depends.remove(myName)
			extPattern.resolve()

		del dependsRev[myName]


def pattern(extPattern):
	extPattern = re.sub(r'\\\s+', '', extPattern)
	def decorate(func):
		childs = {}
		depends = set()
		patternList = []
		anonymousCount = 0
		lastPosition = 0

		for matchObj in re.finditer(r'#\((\w+)(?::(\w+))?\)', extPattern):
			patternType = matchObj.group(1)
			patternName = matchObj.group(2)

			if patternName is None:
				anonymousCount += 1
				patternName = anonymousCount
			elif patternName in childs:
				raise ValueError('%s occured multiple times in extpattern %s' %(patternName, extPattern))

			patternList.append(extPattern[lastPosition:matchObj.start()])
			patternList.append((patternName, patternType))
			lastPosition = matchObj.end()

			if (patternType not in ExtPattern.collection
					or not ExtPattern.collection[patternType].resolvable()):
				depends.add(patternType)
				dependsRev.setdefault(patternType, set()).add(func.__name__)

		patternList.append(extPattern[lastPosition:])
		me = ExtPattern(patternList, func, depends)
		me.resolve()

		def entry(inputStr):
			if not me.resolvable():
				raise RuntimeError('%s not yet resolvable, depends on %s' %
						(me.func.__name__, ', '.join(me.depends)))

			matchObj = re.match(me.calcPattern(), inputStr)
			if matchObj is None: return
			return me.wrap(matchObj)

		return entry
	return decorate

