import requests
import json
from bs4 import BeautifulSoup
import ConfigParser
import urllib
import urlparse
import unicodedata
import requests

fileName = 'vk.cfg'
s = requests.Session()
s.headers.update({'User-Agent':' Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/5.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET4.0C; .NET4.0E)'})


class ApiClient:
	def get_access_token(self):
		params = {
		'client_id':self.app_id,
		'display':'wap',
		'scope':'friends,photos,audio,video,docs,notes,pages,status,offers,questions,wall,groups,messages,notifications,stats,ads,offline',
		'redirect_uri':'http://api.vk.com/blank.html',
		'response_type':'token',
		'hash':0
		}

		query_string = urllib.urlencode(params)
		url = 'http://api.vk.com/oauth/authorize?'+ query_string
		#print "authorization url: " + url
		response = s.get(url)

		#print "response url: " + response.url

		if "act=grant_access" in response.url:
			token = parse_token(response.url)
		if "pass" in response.text:
			token = self.process_login_form(response)
		else:
			print "Error"
			print response.text

		#print token
		return token

	def read_token(self):
		config = ConfigParser.RawConfigParser()
		config.read(fileName)
		
		if "access_token" in config.items("vk"):
			access_token = config.get('vk','access_token')
		else:
			access_token=self.get_access_token()
			config.set('vk','access_token',access_token)

			with open(fileName, 'wb') as configfile:
				config.write(configfile)

		return access_token

	def api(self, method_name, access_token, parameters):
		parameters['access_token']=access_token
		query_string = urllib.urlencode(parameters)
		url = self.url_base+method_name+'?'+query_string
		#print url

		r = requests.get(url)
		return r.json();
	
	def get_profile(uid):
		token = read_token()
		return api('getProfiles',token,{'uid':uid,'fields':'photo_medium_rec,sex,bdate,online'})

	def get_members(self):
		token = self.read_token()

		if token==None:
			return

		group = self.api('groups.getMembers', token, {'gid':'stalobaloba','sort':'time_asc'})

		if 'error' in group:
			print group["error"]
			return

		members = group["response"]["users"]	
		return members

	

	def process_login_form(self,response):
		params={}
		soup = BeautifulSoup(response.text)
		form = soup.form
		for hidden in form.find_all("input",type='hidden'):
			params[hidden["name"]] = hidden["value"]
		
		params["pass"] = self.password
		params["email"]= self.username
		r = s.post(form["action"],params)

		#print "login response url: " + r.url
		url_with_token = r.url
		access_token = self.parse_token(url_with_token)
		return access_token[0]#.encode('ascii','ignore')

	# def read_settings(self):
	# 	config = ConfigParser.RawConfigParser()
	# 	config.read(fileName)
		
	# 	self.url_base = config.get('vk','api_method_url_base')
	#  	self.app_id = config.get('vk','app_id')
	#  	self.app_secret = config.get('vk','app_secret')
	#  	self.username = config.get('vk','username')
	#  	self.password = config.get('vk','password')
	 	
	def parse_token(self,url):
	#print url
		return urlparse.parse_qs(urlparse.urlsplit(url).fragment).get('access_token')

	def __init__(self):
		config = ConfigParser.RawConfigParser()
		config.read(fileName)
		
		self.url_base = config.get('vk','api_method_url_base')
	 	self.app_id = config.get('vk','app_id')
	 	self.app_secret = config.get('vk','app_secret')
	 	self.username = config.get('vk','username')
	 	self.password = config.get('vk','password')	