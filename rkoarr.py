#!/opt/local/bin/python
import urllib.request
import urllib.parse

from bs4 import BeautifulSoup

import json
import re

import argparse

import time

debug = False

# This is where the data lives
url = 'http://register.fin.ee/register/index.php'


# Extract data from the soup tree
# soup - the tree to scrape
# names - array of field names
# type - type of the organization as provided to the scraper
def extractRKOARR(soup, names, type):
	global debug
	t = 0
	o = []
	for line in soup.find_all('tr'):
		td = line.find_all('td')
		if t > 0 and len(td) == len(names):
			c = {}
			i = 0
			for cell in td:
				c[names[i]] = cell.get_text().strip()
				i = i + 1

			c['type'] = type
			o.append(c)

		# For some reason we found less columns than there was headers. Something is amiss: break the loop and print debug
		if debug and len(td) != len(names):
			print('Expected ' + str(len(names)) + ' got ' + str(len(td)))
			print(line)

		t = t + 1
	return o

# Get the content and make it into a soup tree. Then filter out the table we are looking for
# data - the request data to send to server
# tnr - the table number to use. For some reason, there are additional tables in the output 
#       for some org types
def parseContent(data, tnr):
	global debug
	if debug:
		print('Fetching content')
	start = time.clock()

	response = urllib.request.urlopen(url, data.encode('ascii'))
	if debug:
		print('Fetched ' + url + data + ' in ' + str(time.clock() - start) + " sec")

	soup = BeautifulSoup(response.read())                                                                                                           
	return soup.find_all('table')[tnr]

# Fetch the org type list, returns a dictionary of types and their identifiers
# data - the request data to be sent to the server
def getTypes(data):
	global debug

	if debug:
		print('Fetching org types')
	start = time.clock()
	response = urllib.request.urlopen(url, data.encode('ascii'))
	
	if debug:
		print('Fetched ' + url + data + ' in ' + str(time.clock() - start) + " sec")

	soup = BeautifulSoup(response.read())
	r = {}
	for o in soup.find(id='ISS_2_8_1_asuttyyp').find_all('option'):
		if o.get_text().strip() > "":
			r[o['value']] = o.get_text().strip()
	
	return r


# Main logic of the script, calls the rest. 
def donwloadRKOARR(type, p_debug):
	global debug
	debug = p_debug

# Initialize the data structure 
	o = {'meta':{'names':{},'types':getTypes('tunnus=aruanded&report=68')}, 'content':[]}

	values = {	'tunnus':'aruanded', 
			'asutthisType':'1',
			'report':68,
			'slimit':99,
			'action':'searchnow',
			'mode':'now'}


	names = []
# In theory we can loop over the all known type codes. It is more flexible, however, to let the user choose which 
# Organizations are of interest
	#for thisType in [1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 17, 19]:
	for thisType in [type]:
		u = len(o['content'])
		done = False
		page = 1
		while not done:

			data = '?&asuttyyp=' + str(thisType) + '&regname=&tunnus=aruanded&regkoodfrom=&regkoodto=&aadr=&korgkood=&action=searchnow&out=&slimit=999&report=68&page=' + str(page)

			if thisType<11:
				tnr = 9
			else:
				tnr = 8

			content = parseContent(data, tnr)
# Extract column names. Convert the human-readable (unicode) forms to valid field names
			if len(names) == 0:
				for h in content.tr.find_all('font'):
					t = h.string.strip()

					s = re.sub('\s+','_',t.lower())
					s = s.replace('ä','2')
					s = s.replace('ö','o')
					s = s.replace('õ','6')
					s = s.replace('ü','y')
					s = re.sub('[^a-zA-Z0-9_]','',s)
					names.append(s)
			
					o['meta']['names'][s] = t

			p = len(o['content'])
			o['content'].extend(extractRKOARR(content, names, thisType))
			if debug:
				print('Done page ' + str(page) + ' have ' + str(len(o['content'])) + ' items')
		
			page = page + 1
			done = (p == len(o['content']))

		if debug:
			print(str(len(o['content']) - u) + " orgs of type " + str(thisType) + " found")


	return json.dumps(o, sort_keys=False, indent=2)


# Main code body starts here
parser = argparse.ArgumentParser(description='Download RKOARR (official list of Estonian government institutions) data and produce it as JSON output.')
parser.add_argument('type', metavar='ORG_TYPE', type=int, nargs=1, help='Identifies the type of the institutions to download. Values 1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 17, 19 are known to work, their Estonian textual equivalents will be part of the output')

parser.add_argument('--debug', dest='debug', action='store_true', help='Prints debug information thereby invalidating the JSON output') 
args = parser.parse_args()

print(donwloadRKOARR(vars(args)['type'][0], vars(args)['debug']))
