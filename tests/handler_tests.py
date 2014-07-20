import io

from web import web

import fake

from nose.tools import nottest, with_setup

test_message = b'This is a test message.'
test_response = 'OK'

class TestHandler(web.HTTPHandler):
	def do_get(self):
		self.response.headers.set('Test', 'hi')
		return 200, test_response

	def do_put(self):
		return 200, self.request.body

@nottest
def test(method, body='', headers=web.HTTPHeaders(), handler=TestHandler, return_response_obj=False):
	if not isinstance(body, bytes):
		body = body.encode('utf-8')

	request = fake.FakeHTTPRequest(None, ('', 0), None)
	request.method = method.lower()
	request.rfile = io.BytesIO(body)
	request.headers = headers
	request.headers.set('Content-Length', str(len(body)))
	response = request.response

	handler_obj = handler(request, response, ())

	if return_response_obj:
		return response.headers, handler_obj.respond(), response
	else:
		return response.headers, handler_obj.respond()

def test_method():
	headers, response = test('GET')

	#Check response
	assert response[0] == 200
	assert response[1] == test_response

	#Check headers
	assert headers.get('Test') == 'hi'

def test_no_method():
	try:
		headers, response = test('DELETE')
		assert False
	except web.HTTPError as error:
		assert error.code == 405

def test_continue():
	request_headers = web.HTTPHeaders()
	request_headers.set('Expect', '100-continue')

	headers, response, response_obj = test('GET', headers=request_headers, return_response_obj=True)

	#Check response_obj
	print(response_obj.wfile.getvalue())
	assert response_obj.wfile.getvalue() == b'HTTP/1.1 100 Continue\r\n\r\n'

def test_get_body():
	headers, response = test('PUT', body=test_message)

	#Check response
	assert response[0] == 200
	assert response[1] == test_message

def test_body_too_large():
	long_body = fake.FakeBytes()
	long_body.set_len(1048577) #1 byte over 1 MB

	try:
		headers, response = test('PUT', body=long_body)
		assert False
	except web.HTTPError as error:
		assert error.code == 413

def test_options():
	headers, response = test('OPTIONS')

	#Check headers
	allow = headers.get('Allow').split(',')
	assert 'OPTIONS' in allow
	assert 'HEAD' in allow
	assert 'GET' in allow
	assert 'PUT' in allow
	assert len(allow) == 4

	#Check response
	assert response[0] == 204
	assert response[1] == ''

def test_head():
	headers, response, response_obj = test('HEAD', return_response_obj=True)

	#Check headers
	assert headers.get('Test') == 'hi'

	#Check response
	assert response[0] == 200
	assert response[1] == test_response

	#Check response_obj
	assert response_obj.write_body == False
