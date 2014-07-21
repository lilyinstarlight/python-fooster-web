import os
import shutil

import web
import web.file

from http.client import HTTPConnection

test_message = b'This is a test sentence!'

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

class ExceptionHandler(web.HTTPHandler):
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

error_message = b'Oh noes, there was an error!'

class ErrorHandler(web.HTTPErrorHandler):
	def respond(self):
		return 203, error_message

routes = { '/': RootHandler, '/echo': EchoHandler, '/error': ExceptionHandler, '/auth/(.*)': AuthHandler }

web.file.init('tmp', '/tmpro', dir_index=False, modify=False)
web.file.init('tmp', '/tmp', dir_index=True, modify=True)

routes.update(web.file.routes)

def test_integration():
	httpd = web.HTTPServer(('localhost', 0), routes, { '500': ErrorHandler }, log=web.HTTPLog('tmp/httpd.log', 'tmp/access.log'))

	#start
	httpd.start()

	try:
		conn = HTTPConnection('localhost', httpd.server_address[1])

		#test_running
		assert httpd.is_running()

		#test_root
		conn.request('GET', '/')
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == test_message

		#test_echo
		conn.request('GET', '/echo')
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == str

		conn.request('PUT', '/echo', test_message)
		response = conn.getresponse()
		assert response.status == 204
		assert response.read() == b''

		conn.request('GET', '/echo')
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == test_message

		#test_error
		conn.request('GET', '/error')
		response = conn.getresponse()
		assert response.status == 203
		assert response.read() == error_message

		#test_auth
		conn.request('GET', '/auth/')
		response = conn.getresponse()
		assert response.status == 401
		assert response.getheader('WWW-Authenticate') == 'Any'
		response.read()

		conn.request('GET', '/auth/', headers={ 'Authorization': 'None' })
		response = conn.getresponse()
		assert response.status == 404
		response.read()

		conn.request('PUT', '/auth/test', test_message)
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == b'Accepted'

		conn.request('GET', '/auth/test', headers={ 'Authorization': 'None' })
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == test_message

		#test_file_tmp
		conn.request('GET', '/tmp/')
		response = conn.getresponse()
		assert response.status == 200
		response.read()

		response.read()
		conn.request('GET', '/tmp/test')
		response = conn.getresponse()
		assert response.status == 404
		response.read()

		response.read()
		conn.request('PUT', '/tmp/test', test_message)
		response = conn.getresponse()
		assert response.status == 204
		assert response.read() == b''

		response.read()
		conn.request('GET', '/tmp/test')
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == test_message

		#test_file_tmp_ro
		conn.request('GET', '/tmpro/')
		response = conn.getresponse()
		assert response.status == 403
		response.read()

		response.read()
		conn.request('GET', '/tmpro/test')
		response = conn.getresponse()
		assert response.status == 200
		assert response.read() == test_message

		response.read()
		conn.request('PUT', '/tmpro/test', test_message)
		response = conn.getresponse()
		assert response.status == 405
		response.read()
	finally:
		#close
		httpd.close()

		shutil.rmtree('tmp')
