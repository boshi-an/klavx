

import re
from sre_constants import SUCCESS


def givenPattern(pat) :
	def wrapped(string) :
		return pat.match(string)
	return wrapped

def givenRegx(reg) :
	def wrapped(string) :
		res = reg.search(string)
		if res == None :
			return ((0, len(string)), None)
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
		
		pass
	
	@classmethod
	def createPrefixPattern() :

		pass
	
	@classmethod
	def createSelectivePattern() :

		pass

	@classmethod
	def createSuffixPattern() :

		pass
	
	# I used wrapper to view patterns and regxprs the same way
	# pattern(string) = ((l,r), (res1, res2, ...))
	def appendSubPatternSeq(self, subpattern, combiner) :

		wrappedSubPattern = []
		for item in subpattern :
			if type(item) == Pattern :
				wrappedSubPattern.append(givenPattern(item))
			else :
				wrappedSubPattern.append(givenRegx(item))
		self.subPatterns.append(wrappedSubPattern)
		self.combiners.append(combiner)
	
	# match trys every possible pattern sequence to match the given string
	# when one is fit, just return
	def match(self, string) :	# can search on <Pattern> or <re.Match_Object>

		for sequence,combiner in zip(self.subPatterns,self.combiners) :
			curStr = string
			curRes = []
			for sub in sequence :
				res = sub(curStr)
				curRes.append(res[1])
				curStr = curStr[res[0][1]:]
			curSum = combiner(*curRes)
			print(curSum)
			if curSum != None :
				return ((0, curRes[-1]), curSum)
		return None

# TextInterpreter can interpret a string
# pattern and functions are given to the interpreter in pairs
# when only one pattern matches the given string
# the interpreter calls the correspoding function
class TextInterpreter :

	# when there are 0 or more than 1 matches
	# call function whenNone and whenMultiple 
	def __init__(self, whenNone=None, whenMultiple=None) :

		self.patternFuncSeq = []
		self.whenNone = whenNone
		self.whenMultiple = whenMultiple
		pass

	def appendPattern(self, pat, recall) :

		self.patternFuncSeq.append((pat, recall))
	
	# doing interpretation and calling corresponding functions
	def doInterprete(self, string) :

		successNum = 0
		funcParaPair = None
		for pattern,func in self.patternFuncSeq :
			tmp = pattern.match(string)
			if tmp != None :
				_,res = tmp
				funcParaPair = (func, res)
				successNum += 1
		if successNum == 0 :
			if self.whenNone != None :
				self.whenNone()
			return "No interpretation found!"
		elif successNum >= 2 :
			if self.whenMultiple != None :
				self.whenMultiple()
			return "Multiple interpretation found!"
		else :
			funcParaPair[0](*funcParaPair[1])
			return "One interpretation found!"

pReserve = Pattern()
pQuery = Pattern()
pIam = Pattern()
pTime = Pattern()
pDate = Pattern()
pClock = Pattern()
pNumber = Pattern()
pLocation = Pattern()

def initPatterns() :
	pass

if __name__ == '__main__' :

	def m1(para) :
		print("pattern1 matched!")
		print(para)
	
	def m2(para) :
		print("pattern2 matched!")
		print(para)
	
	inter = TextInterpreter()
	
	pat1 = Pattern()
	pat1.appendSubPatternSeq([re.compile(r'[0-9]+'), re.compile(r'\+'), re.compile(r'[0-9]+')], lambda a,b,c:None if a==None or b==None else (int(a)+int(c),))
	inter.appendPattern(pat1, m1)
	inter.doInterprete(input())
	pass