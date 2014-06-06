import mimetypes
import os
import sys
import time

import web

_local = None
_remote = None

route = {}

class FileHandler(web.HTTPHandler):
	def __init__(self, request, response, groups):
		web.HTTPHandler.__init__(self, request, response, groups)
		self.filename = _local + self.groups[0]

	def do_get(self):
		try:
			with open(self.filename, 'r') as file:
				#Guess MIME by extension
				self.response.headers.set('Content-Type', mimetypes.guess_type(self.filename)[0])

				return 200, file.read()
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

	def do_put(self):
		try:
			os.makedirs(os.path.dirname(self.filename), exist_ok=True)
			with open(self.filename, 'w') as file:
				file.write(self.request.rfile.read())

			return 200, ''
		except IOError:
			raise web.HTTPError(403)

	def do_delete(self):
		try:
			os.remove(self.filename)

			return 200, ''
		except IOError:
			raise web.HTTPError(403)

def init(local, remote='/'):
	global _local, _remote, route

	_local = local
	_remote = remote

	route = { remote + '(.*)': FileHandler }

if __name__ == "__main__":
	if len(sys.argv) > 1:
		init(sys.argv[1])
	else:
		init('./')
	web.init(('localhost', 8080), route)
	web.start()
