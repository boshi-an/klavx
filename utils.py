#!/usr/bin/python3
# vim: set noet ts=4 sw=4 fileencoding=utf-8:

def printDict(name, d) :
	print(name, ":")
	for key,val in d.items() :
		print('\t',key,":",val)