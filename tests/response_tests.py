from web import web

import fake

from nose.tools import nottest

@nottest
def test(handler, socket=None, server=None):
	if not socket:
		socket = fake.FakeSocket()

	if not server:
		server = fake.FakeHTTPServer()

	request_obj = fake.FakeHTTPRequest(socket, '', server, handler)
	response_obj = web.HTTPResponse(socket, '', server, request_handler)
	response_obj.handle()
	response_obj.close()

	return response_obj

def test_handler_nonatomic():
	pass

def test_atomic_wait():
	pass

def test_atomic_locking():
	pass

def test_http_error():
	pass

def test_general_error():
	pass

def test_error_headers():
	pass

def test_error_handler():
	pass

def test_response():
	pass

def test_response_status():
	pass

def test_response_io():
	pass

def test_response_io_length():
	pass

def test_response_str():
	pass

def test_response_bytes():
	pass

def test_response_length():
	pass

def test_connection_close():
	pass

def test_error_handler_error():
	pass

def test_no_write_io():
	pass

def test_no_write_bytes():
	pass

def test_write_error():
	pass

def test_log_request():
	pass
