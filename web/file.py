import mimetypes
import os
import sys
import time

import web

_local = None
_remote = None
_modify = False

routes = {}

class FileHandler(web.HTTPHandler):
	def __init__(self, request, response, groups):
		web.HTTPHandler.__init__(self, request, response, groups)
		self.filename = _local + self.groups[0]

	def do_get(self):
		try:
			with open(self.filename, 'rb') as file:
				#Guess MIME by extension
				self.response.headers.set('Content-Type', mimetypes.guess_type(self.filename)[0])

				return 200, file.read()
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

	def do_put(self):
		if not _modify:
			raise web.HTTPError(403)

		try:
			os.makedirs(os.path.dirname(self.filename), exist_ok=True)
			with open(self.filename, 'wb') as file:
				file.write(self.request.body)

			return 200, ''
		except IOError:
			raise web.HTTPError(403)

	def do_delete(self):
		if not _modify:
			raise web.HTTPError(403)

		try:
			os.remove(self.filename)

			return 200, ''
		except IOError:
			raise web.HTTPError(403)

def init(local, remote='/', modify=False):
	global _local, _remote, routes

	if not local.endswith('/'):
		local += '/'
	if not remote.endswith('/'):
		remote += '/'

	_local = local
	_remote = remote
	_modify = modify

	routes = { _remote + '(.*)': FileHandler }

if __name__ == "__main__":
	if len(sys.argv) > 1:
		init(sys.argv[1])
	else:
		init('./')
	web.init(('localhost', 8080), routes)
	web.start()
