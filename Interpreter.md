# 解释器说明

该解释器采用递归的模式匹配方法

对于一个模式，其可以被表示为若干种不同的子模式，如：

- <预约>
	- <预约> = “预约” + <时间段> + <地点>
	- <预约> = “预约” + <地点> + <时间段>
- <时间段>
	- <时间段> = <时间> + “到|至” + <时间>
- <时间>
	- <时间> = <日期> + <时刻>
	- <时间> = <日期>

诸如此类，因此一种模式可以看成是形态不同的树，若一棵树匹配成功，则整个模式匹配成功。叶子节点全部是正则表达式。在一个节点处，每一种子模式对应一个合并函数，合并函数将子模式的含义合并为当前模式的含义。

除了特殊规定，子模式中的相邻两项之间可以任意插入字符，因此如果有时两个子模式互为前缀关系，我们应该先尝试匹配长的模式，再匹配短的模式

这里列举目前已经内置的几种模式：

- Number
	- '[零一二三四五六七八九十0-9日天]+'
- Number_adj
	- '^[零一二三四五六七八九十0-9日天]+'
- Date
	- '今天'
	- '明天'
	- '大\*后天'
	- '下\*个?(周|星期)' + Number_adj
	- Number + '月' + Number_adj
	- Number + '\\.' + Number_adj + '\\.' + Number_adj + '[ ]|$'
	- Number + '\\.' + Number_adj + '[ ]|$'
- SpaseTime
	- '上午|早上'
	- '下午|晚上'
- Clock
	- Number + '\:' + Number_adj + 'am|pm|AM|PM|Am|Pm'
	- Number + '\:|点|时' + Number_adj
	- Number + '^点半'
	- Number + '^点|^时'
- Time
	- Date + SparseTime + Clock + '到|至' + SparseTime + Clock
	- Date + SparseTime + Clock + '到|至' + Clock
	- Date + Clock + '到|至' + Clock
- Location
	- 'B|b' + Number_adj
	- Number
- Reserve
	- '^预约' + Time + Location
	- '^预约' + Time
- Query
	- '^查询' + Time + Location
	- '^查询' + Time
	- '^查询' + Date + Location
	- '^查询' + Date
	- '^查询' + Location
	- '^查询'
- Iam
	- '^我是' + '.*'