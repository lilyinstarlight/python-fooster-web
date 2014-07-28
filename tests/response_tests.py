import io
import threading
import time

from web import web

import fake

from nose.tools import nottest

test_message = b'More test time!'
test_string = test_message.decode('utf-8')

@nottest
def test(handler, handler_args={}, socket=None, server=None):
	if not socket:
		socket = fake.FakeSocket()

	if not server:
		server = fake.FakeHTTPServer()

	request_obj = fake.FakeHTTPRequest(socket, ('', 1337), server, handler=handler, handler_args=handler_args, response=web.HTTPResponse)
	response_obj = request_obj.response
	response_obj.handle()

	value = response_obj.wfile.getvalue()

	response_obj.close()

	#Response line comes before firt '\r\n'
	response_line = value.split('\r\n'.encode(web.http_encoding), 1)[0]

	#Body should happen after '\r\n\r\n' at the end of the HTTP stuff
	body = value.split('\r\n\r\n'.encode(web.http_encoding), 1)[1]

	return response_obj, response_line, response_obj.headers, body

def test_atomic_wait():
	class MyHandler(web.HTTPHandler):
		nonatomic = False

		responded = False

		def respond(self):
			MyHandler.responded = True
			return 200, test_message

	class SpecialHandler(web.HTTPHandler):
		nonatomic = False

		stop = threading.Event()
		waiting = threading.Event()

		def respond(self):
			SpecialHandler.waiting.set()
			SpecialHandler.stop.wait()

			return 204, ''

	#Both must have the same server
	server = fake.FakeHTTPServer()

	#Both handlers should have the same fake resource '/' and should therefore block since they are atomic
	special = threading.Thread(target=test, args=(SpecialHandler,), kwargs={'server': server})
	special.start()

	#Wait until the handler is blocking
	SpecialHandler.waiting.wait(timeout=5)

	#Make sure it is locked
	assert '/' in server.locks

	my = threading.Thread(target=test, args=(MyHandler,), kwargs={'server': server})
	my.start()

	#Not sure how to test that the 'my' thread is stuck in the while loop, but let's hope it is!

	#Join everything
	SpecialHandler.stop.set()
	special.join(timeout=5)
	my.join(timeout=5)

	#Make sure we remove the lock
	assert not '/' in server.locks

def test_http_error():
	response, response_line, headers, body = test(web.DummyHandler, {'error': web.HTTPError(402)})

	assert response_line.startswith('HTTP/1.1 402'.encode(web.http_encoding))

def test_general_error():
	response, response_line, headers, body = test(web.DummyHandler, {'error': TypeError()})

	assert response_line.startswith('HTTP/1.1 500'.encode(web.http_encoding))

def test_error_headers():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			self.response.headers.set('Test', 'True')

			raise web.HTTPError(402)

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Test') == None

def test_error_handler():
	class ErrorHandler(web.HTTPErrorHandler):
		def respond(self):
			self.response.headers.set('Test', 'True')

			return 402, b''

	server = fake.FakeHTTPServer(error_routes={'500': ErrorHandler})

	response, response_line, headers, body = test(web.DummyHandler, {'error': TypeError()}, server=server)

	assert response_line.startswith('HTTP/1.1 402'.encode(web.http_encoding))

	assert headers.get('Test') == 'True'

	assert body == b''

def test_error_handler_error():
	class ErrorHandler(web.HTTPErrorHandler):
		def respond(self):
			raise TypeError()

	server = fake.FakeHTTPServer(error_routes={'500': ErrorHandler})

	response, response_line, headers, body = test(web.DummyHandler, {'error': TypeError()}, server=server)

	assert response_line == 'HTTP/1.1 500 Internal Server Error'.encode(web.http_encoding)

	assert headers.get('Test') == None
	assert headers.get('Content-Length') == '28'

	assert body == b'500 - Internal Server Error\n'

def test_response_io():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			return 200, io.BytesIO(test_message)

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Transfer-Encoding') == 'chunked'
	assert headers.get('Content-Length') == None

	assert body == ('{:x}'.format(len(test_message)) + '\r\n').encode(web.http_encoding) + test_message + '\r\n'.encode(web.http_encoding) + '0\r\n\r\n'.encode(web.http_encoding)

def test_response_io_length():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			self.response.headers.set('Content-Length', '2')

			return 200, io.BytesIO(test_message)

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Content-Length') == '2'

	assert body == test_message[0:2]

def test_response_str():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			return 200, test_message.decode('utf-8')

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Content-Length') == str(len(test_message))

	assert body == test_message

def test_response_bytes():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			return 200, test_message

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Content-Length') == str(len(test_message))

	assert body == test_message

def test_response_length():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			self.response.headers.set('Content-Length', '2')

			return 200, test_message

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Content-Length') == '2'

	assert body == test_message

def test_connection_close():
	class MyHandler(web.HTTPHandler):
		def respond(self):
			return 204, ''

	response, response_line, headers, body = test(MyHandler)

	assert headers.get('Connection') == None

	class CloseHandler(web.HTTPHandler):
		def respond(self):
			self.request.keepalive = False

			return 204, ''

	response, response_line, headers, body = test(CloseHandler)

	assert headers.get('Connection') == 'close'

def test_error_headers():
	pass

def test_no_write_io():
	pass

def test_no_write_bytes():
	pass

def test_write_error():
	pass

def test_log_request():
	pass
