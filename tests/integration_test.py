import os
import shutil

import web
import web.file

from nose.tools import with_setup

test_message = 'This is a test sentence!'

class RootHandler(web.HTTPHandler):
	def do_get(self):
		return 200, test_message

str = b''

class EchoHandler(web.HTTPHandler):
	def do_get(self):
		global str

		return 200, str

	def do_put(self):
		global str

		str = self.request.body

		return 204, ''

class ErrorHandler(web.HTTPHandler):
	def do_get(self):
		raise Exception()

saved = {}

class AuthHandler(web.HTTPHandler):
	def do_get(self):
		if not self.request.headers.get('Authorization'):
			auth_headers = web.HTTPHeaders()
			auth_headers.set('WWW-Authenticate', 'Any')
			raise web.HTTPError(401, headers=auth_headers)

		body = saved.get(self.groups[0])

		if not body:
			raise web.HTTPError(404)

		return 200, body

	def do_put(self):
		saved[self.groups[0]] = self.request.body

		return 200, 'Accepted'

routes = { '/': RootHandler, '/echo': EchoHandler, '/error': ErrorHandler, '/auth/(.*)': AuthHandler }

web.file.init('tmp', '/tmpro', dir_index=False, modify=False)
web.file.init('tmp', '/tmp', dir_index=True, modify=True)

routes.update(web.file.routes)

httpd = web.HTTPServer(('localhost', 8080), routes, log=web.HTTPLog('tmp/httpd.log', 'tmp/access.log'))
httpd.start()

def test_running():
	assert httpd.is_running()

def test_root():
	pass

def test_echo():
	pass

def test_auth():
	pass

def setup_file():
	pass

def teardown_file():
	pass

@with_setup(setup_file, teardown_file)
def test_file_tmp():
	pass

@with_setup(setup_file, teardown_file)
def test_file_tmp_ro():
	pass

def test_close():
	httpd.close()

	shutil.rmtree('tmp')
