import os
import time

import web

_local = None
_remote = None

route = {}

class FileHandler(web.HTTPHandler):
	def do_get(self):
		try:
			with open(_local + self.groups[0], 'r') as file:
				if self.groups[0].endswith('.html'):
					self.response.headers.set('Content-Type', 'text/html; charset=utf-8')
				elif self.groups[0].endswith('.png'):
					self.response.headers.set('Content-Type', 'image/png')
				elif self.groups[0].endswith('.css'):
					self.response.headers.set('Content-Type', 'text/css; charset=utf-8')
				elif self.groups[0].endswith('.js'):
					self.response.headers.set('Content-Type', 'application/javascript; charset=utf-8')
				else:
					self.response.headers.set('Content-Type', 'text/plain; charset=utf-8')

				return 200, file.read()
		except FileNotFoundError:
			raise web.HTTPError(404)
		except IOError:
			raise web.HTTPError(403)

	def do_put(self):
		try:
			os.remove(_local + self.groups[0])
		except IOError:
			raise web.HTTPError(403)

	def do_delete(self):
		try:
			with open(_local + self.groups[0], 'w') as file:
				file.write(self.request.rfile.read())
		except IOError:
			raise web.HTTPError(403)

def init(local, remote='/'):
	global _local, _remote, route

	_local = local
	_remote = remote

	route = { remote + '(.*)': FileHandler }

if __name__ == "__main__":
	init('./')
	web.init(('localhost', 8080), route)
	web.start()
