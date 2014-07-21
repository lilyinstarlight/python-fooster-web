from web import web

import fake

from nose.tools import nottest

@nottest
def test(socket=None, server=None, timeout=None):
	if not socket:
		socket = fake.FakeSocket()

	if not server:
		server = fake.FakeHTTPServer()

	request_handler = web.HTTPRequestHandler(socket, '', server, timeout)
	request_handler.response = fake.FakeHTTPResponse(socket, '', server, request_handler)
	request_handler.handle()
	request_handler.close()

	return request_handler

def test_initial_timeout():
	pass

def test_no_request():
	pass

def test_request_too_large():
	pass

def test_no_newline():
	pass

def test_bad_request_line():
	pass

def test_wrong_http_version():
	pass

def test_header_too_large():
	pass

def test_too_many_headers():
	pass

def test_header_no_newline():
	pass

def test_header_no_colon():
	pass

def test_connection_close():
	pass

def test_handler_not_found():
	pass
