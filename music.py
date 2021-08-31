# vim: set noet ts=4 sw=4 fileencoding=utf-8:

import random
import sqlite3

conn = sqlite3.connect('music.db')

def randomMusic():
	curs = conn.cursor()
	curs.execute('SELECT COUNT(*) FROM song')
	count = curs.fetchone()[0]

	num = random.randrange(count)
	curs = conn.cursor()
	curs.execute('SELECT song.title, song.url, album.image '
			'FROM song JOIN album ON song.albumId=album.id '
			'WHERE song.id>=? ORDER BY song.id LIMIT 1', (num,))

	title, url, image = curs.fetchone()
	return dict(title=title, url=url, image=image)


if __name__=='__main__':
	print(randomMusic())
	print(randomMusic())
	print(randomMusic())
