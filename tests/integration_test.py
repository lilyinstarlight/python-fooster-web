import io
import os
import shutil

import web
import web.file

from http.client import HTTPConnection, HTTPSConnection

from nose.tools import nottest

test_message = b'This is a test sentence!'

class RootHandler(web.HTTPHandler):
	def do_get(self):
		return 200, test_message

class IOHandler(web.HTTPHandler):
	def do_get(self):
		self.response.headers.set('content-length', str(len(test_message)))
		return 200, io.BytesIO(test_message)

class ChunkedHandler(web.HTTPHandler):
	def do_get(self):
		#Create a multichunked 'aaaaaaa...' message
		return 200, io.BytesIO(test_message + b''.join(b'a' for i in range(web.stream_chunk_size)) + test_message)

class ExceptionHandler(web.HTTPHandler):
	def do_get(self):
		raise Exception()

string = b''

class EchoHandler(web.HTTPHandler):
	def do_get(self):
		global string

		return 200, string

	def do_put(self):
		global string

		string = self.request.body

		return 204, ''

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

routes = { '/': RootHandler, '/io': IOHandler, '/chunked': ChunkedHandler, '/error': ExceptionHandler, '/echo': EchoHandler, '/auth/(.*)': AuthHandler }

routes.update(web.file.new('tmp', '/tmpro', dir_index=False, modify=False))
routes.update(web.file.new('tmp', '/tmp', dir_index=True, modify=True))

def test_integration():
	httpd = web.HTTPServer(('localhost', 0), routes, { '500': ErrorHandler }, log=web.HTTPLog('tmp/httpd.log', 'tmp/access.log'))
	httpsd = web.HTTPServer(('localhost', 0), routes, { '500': ErrorHandler }, keyfile='tests/ssl/ssl.key', certfile='tests/ssl/ssl.crt', log=web.HTTPLog('tmp/httpd_ssl.log', 'tmp/access_ssl.log'))

	#start
	httpd.start()
	httpsd.start()

	#test_running
	assert httpd.is_running()
	assert httpsd.is_running()

	try:
		conn = HTTPConnection('localhost', httpd.server_address[1])
		conn_ssl = HTTPSConnection('localhost', httpsd.server_address[1])
		print('No SSL')
		run_conn_tests(conn)
		print('Using SSL')
		run_conn_tests(conn_ssl)
	finally:
		#close
		httpd.close()
		httpsd.close()

		shutil.rmtree('tmp')

@nottest
def run_conn_tests(conn):
	#test_root
	conn.request('GET', '/')
	response = conn.getresponse()
	assert response.status == 200
	assert response.read() == test_message

	#test_io
	conn.request('GET', '/io')
	response = conn.getresponse()
	assert response.status == 200
	assert response.read() == test_message

	#test_chunked
	conn.request('GET', '/chunked')
	response = conn.getresponse()
	assert response.status == 200
	assert response.getheader('Transfer-Encoding') == 'chunked'
	text = response.read()
	assert text.startswith(test_message)
	assert text[len(test_message)] == ord(b'a')
	assert text.endswith(test_message)

	#test_error
	conn.request('GET', '/error')
	response = conn.getresponse()
	assert response.status == 203
	assert response.read() == error_message

	#test_echo
	conn.request('GET', '/echo')
	response = conn.getresponse()
	assert response.status == 200
	assert response.read() == string

	conn.request('PUT', '/echo', test_message)
	response = conn.getresponse()
	assert response.status == 204
	assert response.read() == b''

	conn.request('GET', '/echo')
	response = conn.getresponse()
	assert response.status == 200
	assert response.read() == test_message

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
	conn.request('PUT', '/tmpro/test')
	response = conn.getresponse()
	assert response.status == 405
	response.read()

	#test_file_delete
	response.read()
	conn.request('DELETE', '/tmp/test')
	response = conn.getresponse()
	assert response.status == 204
	assert response.read() == b''
