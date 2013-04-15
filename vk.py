# -*- coding: utf-8 -*-
import ConfigParser
import shelve
import sqlite3 as lite

import json
import pyzmail

from datetime import datetime,  timedelta
from vk_api import ApiClient 

fileName = 'vk.cfg'

# shelve_file = "vk.shelf"
# db_name = "vk.db"
# api_method_url_base  = "https://api.vk.com/method/"

# app_id = 3362438
# app_secret = 'x4hGokusolKNorGHyoZA'
# username = 'bumashechka@gmail.com'
# password = 'xasiYezix'

'''
event_type:
0 - joined
1 - left
'''

def main():
	settings = read_settings()

	init_db(settings['db_name'])

	api = ApiClient()

	current_members_list = api.get_members()
	last_members_list = get_current_members(settings['db_name'])

	new_users = list(set(current_members_list) - set(last_members_list))
	left_users = list(set(last_members_list) - set(current_members_list))

	print "NEW USERS"
	print new_users
	print "LEFT USERS"
	print left_users

	add_joined(new_users, settings['db_name'])
	removed_users = remove_left(left_users, settings['db_name'])
	
	send_mail(settings,new_users,removed_users)
	
	return

def init_db(db_name):
	con = lite.connect(db_name)

	with con:
		cur = con.cursor()
		cur.executescript("""

			CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, joined_at DATE, left_at DATE, is_in_group INT DEFAULT 1);

			CREATE TABLE IF NOT EXISTS events
			(	
				id INTEGER PRIMARY KEY AUTOINCREMENT,
			 	user_id INTEGER REFERENCES Users(id),
			 	happened_at DATE,
			 	event_type INTEGER
			);

			CREATE INDEX IF NOT EXISTS main.events_by_time ON events (happened_at, event_type);

			CREATE INDEX IF NOT EXISTS main.current_users ON users (is_in_group DESC);
			""")

	# current_members = read_members()	
	# add_joined(current_members)

def members_to_tuple(members):
	return tuple(map(lambda m: (m,), members))

def get_current_members(db_name):
	con = lite.connect(db_name)
	con.row_factory = lite.Row

	with con:    
	    cur = con.cursor()
	    cur.execute("SELECT id from users where is_in_group=1")
	    ids = [row['id'] for row in cur.fetchall()]

	return ids 


def add_joined(members, db_name):
	con = lite.connect(db_name)
	members_tuple = members_to_tuple(members)

	with con:    
	    cur = con.cursor()
	    cur.executemany("INSERT INTO Users(id,joined_at) VALUES(?, date('now'))", members_tuple)
	    cur.executemany("INSERT INTO Events(user_id,happened_at,event_type) VALUES(?, date('now'),0)", members_tuple)

def remove_left(members,db_name):
	con = lite.connect(db_name,detect_types=lite.PARSE_DECLTYPES)
	con.row_factory = lite.Row

	members_tuple = members_to_tuple(members)

	with con:    
	    cur = con.cursor()
	    cur.executemany("INSERT INTO Events(user_id,happened_at,event_type) VALUES(?,date('now'),1)", members_tuple)
	    cur.execute("UPDATE Users SET is_in_group=0, left_at=date('now') WHERE id IN (SELECT u.id FROM  Users u JOIN Events e ON e.happened_at = date('now') AND e.user_id=u.id AND event_type=1)")
	    cur.execute("SELECT u.id, u.joined_at FROM Users u JOIN Events e ON e.happened_at = date('now') AND e.user_id=u.id AND event_type=1")
	    rows = cur.fetchall()
	    return rows

def read_settings():
	config = ConfigParser.RawConfigParser()
	config.read(fileName)

	settings = {
		'shelve_file' : config.get('main','shelve_file'),
		'db_name' : config.get('main','db_name'),
		'smtp_host':config.get('mail','smtp_host'),
		'smtp_port':config.getint('mail','smtp_port'),
		'smtp_mode':config.get('mail','smtp_mode'),
		'smtp_login':config.get('mail','smtp_login'),
		'smtp_password':config.get('mail','smtp_password'),
		'recipients' : config.get('mail','recipients').split(', '),
	}

 	return settings
	
def build_profile_url(id):
	return 'http://vk.com/id{0}'.format(str(id))

def profile_li(id):
	url = build_profile_url(id)
	return '<li><a href="{0}"></a>{0}</li>'.format(url)

def left_profile_li(row):
	url = build_profile_url(row['id'])
	joined_at = row['joined_at']
	return '<li><a href="{0}"></a>{0} (был(а) в группе {1} дней)</li>'.format(url,(datetime.now()-joined_at).days)

def send_mail(settings,joined, removed):
	compose_mail(settings,joined, removed)
	#process_mail(payload)

def unshelve_or_none(key, shelve_file):
	shelf = shelve.open(shelve_file)
	if shelf.has_key(key):
		val = shelf[key]
		shelf.close()
		return val
	shelf.close()

	return None

def put_to_shelve(key, val, shelve_file):
	shelf = shelve.open(shelve_file)
	shelf[key]=val
	shelf.close()

def compose_mail(settings, joined, left):	
	sender=(u'Питон', 'robot@stalobaloba.ru')
	recipients=settings['recipients']

	subject=u'{0} in, {1} out'.format(len(joined),len(left))
	text_content=u'' # u'Bonjour aux Fran\xe7ais'
	encoding='utf-8'

	joined_html = ''.join (map(profile_li,joined))
	left_html = ''.join (map(left_profile_li,left))

	now = datetime.now()
	last_run = unshelve_or_none('last_run', settings['shelve_file'])
	put_to_shelve('last_run', now, settings['shelve_file'])

	datestring = '{0:%d/%m/%y}'.format(now)

	if last_run:
		delta = now - last_run

		if delta.days < 1:
			datestring = '{0:%d/%m/%y %H:%M} - {1:%H:%M}'.format(last_run, now)
		elif delta.seconds>100:
			datestring = '{0:%d/%m/%y %H:%M} - {1:%d/%m/%y %H:%M}'.format(last_run, now)

	html_content=u'<html><body><h1>Отчет о группе {0}<h1><h2>Новые пользователи</h2><ul>{1}</ul>\
					<h2>Вышедшие пользователи</h2><ul>{2}</ul></body></html>'.format(datestring,joined_html,left_html)

	payload, mail_from, rcpt_to, msg_id=pyzmail.compose_mail(\
	        sender, \
	        recipients, \
	        subject, \
	        encoding, \
	       	None\
	        ,(html_content, encoding))

	ret=pyzmail.send_mail(payload, mail_from, rcpt_to, settings['smtp_host'], \
	        smtp_port=settings['smtp_port'], smtp_mode=settings['smtp_mode'], \
	        smtp_login=settings['smtp_login'], smtp_password=settings['smtp_password'])

	if isinstance(ret, dict):
	    if ret:
	        print 'failed recipients:', ', '.join(ret.keys())
	    else:
	        print 'success'
	else:
	    print 'error:', ret

if __name__ == "__main__":
    main()