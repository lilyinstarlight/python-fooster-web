import io

import fake

message = 'This is just a test'

def make_log(httpd_log=-1, access_log=-1):
	if httpd_log == -1:
		httpd_log = io.StringIO('')
	if access_log == -1:
		access_log = io.StringIO('')

	return fake.FakeHTTPLog(httpd_log, access_log)

def test_log_none():
	log = make_log(None, None)

	assert hasattr(log, 'httpd_log')
	assert hasattr(log.httpd_log, 'write')

	assert hasattr(log, 'access_log')
	assert hasattr(log.access_log, 'write')

def test_message():
	log = make_log()

	log.message(message)
	value = log.httpd_log.getvalue()

	assert value.endswith(message + '\n')

def test_info():
	log = make_log()

	log.info(message)
	value = log.httpd_log.getvalue()

	assert value.endswith('INFO: ' + message + '\n')

def test_warn():
	log = make_log()

	log.warn(message)
	value = log.httpd_log.getvalue()

	assert value.endswith('WARN: ' + message + '\n')

def test_error():
	log = make_log()

	log.error(message)
	value = log.httpd_log.getvalue()

	assert value.endswith('ERROR: ' + message + '\n')

def test_exception():
	log = make_log()

	try:
		raise Exception()
	except:
		log.exception()
	value = log.httpd_log.getvalue().splitlines()[0]

	assert value.endswith('ERROR: Caught exception:')

def test_request():
	log = make_log()

	log.request('localhost', 'GET / HTTP/1.1', '200', '1024', '-', '-')
	value = log.access_log.getvalue()

	#Test for standard HTTP log format

	assert value.startswith('localhost - - [')
	#Timestamp here
	assert value.endswith('] "GET / HTTP/1.1" 200 1024\n')
