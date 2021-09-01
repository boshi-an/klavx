import random

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