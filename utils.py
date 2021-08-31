#!/usr/bin/python3
# vim: set noet ts=4 sw=4 fileencoding=utf-8:

import datetime

def currentDate():
	return datetime.datetime.now().date()


def toDatetime(date):
	return datetime.datetime.combine(date, datetime.time())
