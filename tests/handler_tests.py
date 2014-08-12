from web import web

import fake

from nose.tools import nottest

test_message = b'This is a test message.'
test_response = 'OK'
test_status = 'Befuddled'

class TestHandler(web.HTTPHandler):
	def do_get(self):
		self.response.headers.set('Test', 'hi')
		return 200, test_response

	def do_put(self):
		return 200, self.request.body

@nottest
def test(method, body='', headers=web.HTTPHeaders(), handler=TestHandler, handler_args={}, return_response_obj=False):
	if not isinstance(body, bytes):
		body = body.encode('utf-8')

	request = fake.FakeHTTPRequest(None, ('', 1337), None, body=body, headers=headers, method=method, handler=handler, handler_args=handler_args)

	handler_obj = request.handler

	if return_response_obj:
		return request.response.headers, handler_obj.respond(), handler_obj.response
	else:
		return request.response.headers, handler_obj.respond()

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
	assert response_obj.wfile.getvalue() == b'HTTP/1.1 100 Continue\r\n\r\n'

def test_get_body():
	headers, response = test('PUT', body=test_message)

	#Check response
	assert response[0] == 200
	assert response[1] == test_message

def test_body_too_large():
	long_body = fake.FakeBytes()
	long_body.set_len(web.max_request_size + 1)

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

def test_dummy_handler():
	test_error = Exception()
	try:
		headers, response = test('GET', handler=web.DummyHandler, handler_args={'error': test_error})
		assert False
	except Exception as error:
		assert error is test_error

def test_error_handler():
	test_error = web.HTTPError(102)

	headers, response = test('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

	assert response[0] == test_error.code
	assert response[1] == web.status_messages[test_error.code]
	assert response[2] == str(test_error.code) + ' - ' + web.status_messages[test_error.code] + '\n'

def test_error_handler_status():
	test_error = web.HTTPError(102, status_message=test_status)

	headers, response = test('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

	assert response[0] == test_error.code
	assert response[1] == test_status
	assert response[2] == str(test_error.code) + ' - ' + test_status + '\n'

def test_error_handler_message():
	test_error = web.HTTPError(102, test_message)

	headers, response = test('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

	assert response[0] == test_error.code
	assert response[1] == web.status_messages[test_error.code]
	assert response[2] == test_message

def test_error_handler_status_message():
	test_error = web.HTTPError(102, test_message, status_message=test_status)

	headers, response = test('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

	assert response[0] == test_error.code
	assert response[1] == test_status
	assert response[2] == test_message
