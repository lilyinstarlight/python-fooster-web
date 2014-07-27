import stat
import os
import shutil

from web import web, file

import fake

from nose.tools import with_setup, nottest

test_string = b'secret test message'

@nottest
def test(method, resource, body='', headers=web.HTTPHeaders(), handler=None, local='tmp', remote='', dir_index=False, modify=False):
	if not isinstance(body, bytes):
		body = body.encode('utf-8')

	if not handler:
		route = file.new(local, remote, dir_index, modify)

		if remote.endswith('/'):
			#Make sure remote trailing slash is removed if necessary
			assert list(route.keys())[0].startswith(remote[:-1] + '(')

		handler = list(route.values())[0]

	request = fake.FakeHTTPRequest(None, ('', 0), None, body=body, headers=headers, method=method, resource=resource, groups=(resource[len(remote):],), handler=handler)

	handler_obj = request.handler

	if local.endswith('/'):
		#Make sure local trailing slash is removed if necessary and filename is set correctly
		assert handler_obj.filename == local[:-1] + handler_obj.groups[0]

	return request.response.headers, handler_obj.respond()

def test_trailing_slashes():
	headers, response = test('GET', '/', local='./', remote='/')

def setup_get():
	if os.path.exists('tmp'):
		shutil.rmtree('tmp')

	os.mkdir('tmp')
	with open('tmp/test', 'wb') as file:
		file.write(test_string)
	with open('tmp/test.txt', 'wb') as file:
		file.write(test_string)
	with open('tmp/forbidden', 'wb') as file:
		pass
	os.chmod('tmp/forbidden', stat.S_IWRITE)
	os.mkdir('tmp/testdir')
	with open('tmp/testdir/magic', 'wb') as file:
		pass
	os.mkdir('tmp/indexdir')
	with open('tmp/indexdir/index.html', 'wb') as file:
		file.write(test_string)

def teardown_get():
	shutil.rmtree('tmp')

@with_setup(setup_get, teardown_get)
def test_get_file():
	headers, response = test('GET', '/test')

	#Check headers
	assert int(headers.get('Content-Length')) == len(test_string)
	assert headers.get('Accept-Ranges') == 'bytes'
	assert headers.get('Content-Type') == None
	assert headers.get('Content-Range') == None

	#Check response
	assert response[0] == 200
	assert response[1].read() == test_string

@with_setup(setup_get, teardown_get)
def test_get_range():
	range = 2, 6
	length = range[1] - range[0] + 1

	request_headers = web.HTTPHeaders()
	request_headers.set('Range', 'bytes=' + str(range[0]) + '-' + str(range[1]))
	headers, response = test('GET', '/test', headers=request_headers)

	#Check headers
	assert int(headers.get('Content-Length')) == length
	assert headers.get('Accept-Ranges') == 'bytes'
	assert headers.get('Content-Type') == None
	assert headers.get('Content-Range') == 'bytes ' + str(range[0]) + '-' + str(range[1]) + '/' + str(len(test_string))

	#Check response
	assert response[0] == 206
	assert response[1].read(length) == test_string[range[0]:range[1]+1]

@with_setup(setup_get, teardown_get)
def test_get_open_range():
	lower = 2
	length = len(test_string) - lower

	request_headers = web.HTTPHeaders()
	request_headers.set('Range', 'bytes=' + str(lower) + '-')
	headers, response = test('GET', '/test', headers=request_headers)

	#Check headers
	assert int(headers.get('Content-Length')) == length
	assert headers.get('Accept-Ranges') == 'bytes'
	assert headers.get('Content-Type') == None
	assert headers.get('Content-Range') == 'bytes ' + str(lower) + '-' + str(len(test_string) - 1) + '/' + str(len(test_string))

	#Check response
	assert response[0] == 206
	assert response[1].read(length) == test_string[lower:]

@with_setup(setup_get, teardown_get)
def test_get_mime():
	headers, response = test('GET', '/test.txt')

	#Check headers
	assert int(headers.get('Content-Length')) == len(test_string)
	assert headers.get('Accept-Ranges') == 'bytes'
	assert headers.get('Content-Type') == 'text/plain'
	assert headers.get('Content-Range') == None

	#Check response
	assert response[0] == 200
	assert response[1].read() == test_string

@with_setup(setup_get, teardown_get)
def test_get_notfound():
	try:
		headers, response = test('GET', '/nonexistent')
		assert False
	except web.HTTPError as error:
		assert error.code == 404

	try:
		headers, response = test('GET', '/test/')
		assert False
	except web.HTTPError as error:
		assert error.code == 404

	try:
		headers, response = test('GET', '/test/nonexistent')
		assert False
	except web.HTTPError as error:
		assert error.code == 404

@with_setup(setup_get, teardown_get)
def test_get_forbidden():
	try:
		headers, response = test('GET', '/forbidden')
		assert False
	except web.HTTPError as error:
		assert error.code == 403

@with_setup(setup_get, teardown_get)
def test_get_dir():
	headers, response = test('GET', '/testdir')

	#Check headers
	assert headers.get('Location') == '/testdir/'

	#Check resposne
	assert response[0] == 307
	assert response[1] == ''

@with_setup(setup_get, teardown_get)
def test_get_dir_index_listing():
	headers, response = test('GET', '/testdir/', dir_index=True)

	#Check resposne
	assert response[0] == 200
	assert response[1] == 'magic\n'

@with_setup(setup_get, teardown_get)
def test_get_no_dir_index_listing():
	try:
		headers, response = test('GET', '/testdir/')
		assert False
	except web.HTTPError as error:
		assert error.code == 403

@with_setup(setup_get, teardown_get)
def test_get_dir_index_file():
	headers, response = test('GET', '/indexdir/')

	#Check headers
	assert headers.get('Content-Type') == 'text/html'
	assert int(headers.get('Content-Length')) == len(test_string)

	#Check resposne
	assert response[0] == 200
	assert response[1].read() == test_string

@with_setup(setup_get, teardown_get)
def test_get_custom_handler():
	class MyHandler(file.FileHandler):
		filename = 'tmp/test'

	headers, response = test('GET', '/', handler=MyHandler)

	#Check headers
	assert int(headers.get('Content-Length')) == len(test_string)
	assert headers.get('Accept-Ranges') == 'bytes'
	assert headers.get('Content-Type') == None
	assert headers.get('Content-Range') == None

	#Check response
	assert response[0] == 200
	assert response[1].read() == test_string

	#Try dir_index
	class MyHandler(file.FileHandler):
		filename = 'tmp/testdir/'
		dir_index = True

	headers, response = test('GET', '/', handler=MyHandler)

	#Check resposne
	assert response[0] == 200
	assert response[1] == 'magic\n'

	#Try index function
	class MyHandler(file.FileHandler):
		filename = 'tmp/testdir/'
		dir_index = True

		def index(self):
			return test_string

	headers, response = test('GET', '/', handler=MyHandler)

	#Check resposne
	assert response[0] == 200
	assert response[1] == test_string

def setup_put():
	if os.path.exists('tmp'):
		shutil.rmtree('tmp')

	os.mkdir('tmp')
	with open('tmp/exists', 'wb') as file:
		pass
	with open('tmp/forbidden', 'wb') as file:
		pass
	os.chmod('tmp/forbidden', stat.S_IREAD)

def teardown_put():
	shutil.rmtree('tmp')

@with_setup(setup_put, teardown_put)
def test_put_file():
	headers, response = test('PUT', '/test', body=test_string, modify=True)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	headers, response = test('GET', '/test')

	#Check response
	assert response[0] == 200
	assert response[1].read() == test_string

@with_setup(setup_put, teardown_put)
def test_put_existing_file():
	headers, response = test('PUT', '/exists', body=test_string, modify=True)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	headers, response = test('GET', '/exists')

	#Check response
	assert response[0] == 200
	assert response[1].read() == test_string

@with_setup(setup_put, teardown_put)
def test_put_forbidden():
	try:
		headers, response = test('PUT', '/forbidden', body=test_string, modify=True)
		assert False
	except web.HTTPError as error:
		assert error.code == 403

	headers, response = test('GET', '/forbidden')

	#Check response
	assert response[0] == 200
	assert response[1].read() != test_string

@with_setup(setup_put, teardown_put)
def test_put_dir():
	headers, response = test('PUT', '/testdir/', body=test_string, modify=True)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	headers, response = test('GET', '/testdir/', dir_index=True)

	#Check response
	assert response[0] == 200
	assert response[1] == ''

@with_setup(setup_put, teardown_put)
def test_put_nomodify():
	try:
		headers, response = test('PUT', '/test', body=test_string, modify=False)
		assert False
	except web.HTTPError as error:
		assert error.code == 405

@with_setup(setup_put, teardown_put)
def test_put_custom_handler():
	class MyHandler(file.ModifyFileHandler):
		filename = 'tmp/test'

	headers, response = test('PUT', '/', body=test_string, handler=MyHandler)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	headers, response = test('GET', '/', handler=MyHandler)

	#Check response
	assert response[0] == 200
	assert response[1].read() == test_string

@with_setup(setup_put, teardown_put)
def test_put_custom_handler_nomodify():
	class MyHandler(file.FileHandler):
		filename = 'tmp/test'

	try:
		headers, response = test('PUT', '/', body=test_string, handler=MyHandler)
		assert False
	except web.HTTPError as error:
		assert error.code == 405

def setup_delete():
	if os.path.exists('tmp'):
		shutil.rmtree('tmp')

	os.mkdir('tmp')
	with open('tmp/test', 'wb') as file:
		pass
	with open('tmp/forbidden', 'wb') as file:
		pass
	os.mkdir('tmp/forbiddendir')
	os.chmod('tmp/forbiddendir/', stat.S_IREAD)
	os.mkdir('tmp/testdir')

def teardown_delete():
	shutil.rmtree('tmp')

@with_setup(setup_delete, teardown_delete)
def test_delete_file():
	headers, response = test('DELETE', '/test', modify=True)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	try:
		headers, response = test('GET', '/test')
		assert False
	except web.HTTPError as error:
		assert error.code == 404

@with_setup(setup_delete, teardown_delete)
def test_delete_nonexistent():
	try:
		headers, response = test('DELETE', '/nonexistent', modify=True)
		assert False
	except web.HTTPError as error:
		assert error.code == 404

@with_setup(setup_delete, teardown_delete)
def test_delete_forbidden():
	try:
		headers, response = test('DELETE', '/forbiddendir/forbidden', modify=True)
		assert False
	except web.HTTPError as error:
		assert error.code == 403

@with_setup(setup_delete, teardown_delete)
def test_delete_dir():
	headers, response = test('DELETE', '/testdir', modify=True)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	try:
		headers, response = test('GET', '/testdir')
		assert False
	except web.HTTPError as error:
		assert error.code == 404

@with_setup(setup_delete, teardown_delete)
def test_delete_nomodify():
	try:
		headers, response = test('DELETE', '/test', modify=False)
		assert False
	except web.HTTPError as error:
		assert error.code == 405

@with_setup(setup_delete, teardown_delete)
def test_delete_custom_handler():
	class MyHandler(file.ModifyFileHandler):
		filename = 'tmp/test'

	headers, response = test('DELETE', '/', handler=MyHandler)

	#Check response
	assert response[0] == 204
	assert response[1] == ''

	try:
		headers, response = test('GET', '/', handler=MyHandler)
		assert False
	except web.HTTPError as error:
		assert error.code == 404

@with_setup(setup_delete, teardown_delete)
def test_delete_custom_handler_nomodify():
	class MyHandler(file.FileHandler):
		filename = 'tmp/test'

	try:
		headers, response = test('DELETE', '/', handler=MyHandler)
		assert False
	except web.HTTPError as error:
		assert error.code == 405
