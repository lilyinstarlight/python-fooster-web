import io
import stat
import os
import shutil

from web import web, file

import fake

from nose.tools import with_setup, nottest

test_string = b'secret test message'

@nottest
def test(method, resource, body='', headers=web.HTTPHeaders(), handler=None, local='tmp', remote='', dir_index=False, modify=False):
	bytebody = body.encode('utf-8')

	if not handler:
		file.init(local, remote, dir_index, modify)

		if remote.endswith('/'):
			#Make sure remote trailing slash is removed if necessary
			assert list(file.routes.keys())[0].startswith(remote[:-1] + '(')

		handler = list(file.routes.values())[0]
		file.routes.clear()

	request = fake.FakeHTTPRequest(None, ( '', 0 ), None)
	request.method = method.lower()
	request.resource = resource
	request.rfile = io.BytesIO(bytebody)
	request.headers = headers
	request.headers.set('Content-Length', str(len(bytebody)))
	response = request.response
	groups = ( resource[len(remote):], )

	handler_obj = handler(request, response, groups)

	if local.endswith('/'):
		#Make sure local trailing slash is removed if necessary and filename is set correctly
		assert handler_obj.filename == local[:-1] + groups[0]

	return response.headers, handler_obj.respond()

def test_trailing_slashes():
	test('GET', '/', local='.', remote='/')

def setup_test_get():
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

def teardown_test_get():
	os.remove('tmp/indexdir/index.html')
	os.rmdir('tmp/indexdir')
	os.remove('tmp/testdir/magic')
	os.rmdir('tmp/testdir')
	os.remove('tmp/forbidden')
	os.remove('tmp/test.txt')
	os.remove('tmp/test')
	os.rmdir('tmp')

@with_setup(setup_test_get, teardown_test_get)
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

@with_setup(setup_test_get, teardown_test_get)
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

@with_setup(setup_test_get, teardown_test_get)
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

@with_setup(setup_test_get, teardown_test_get)
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

@with_setup(setup_test_get, teardown_test_get)
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

@with_setup(setup_test_get, teardown_test_get)
def test_get_forbidden():
	try:
		headers, response = test('GET', '/forbidden')
		assert False
	except web.HTTPError as error:
		assert error.code == 403

@with_setup(setup_test_get, teardown_test_get)
def test_get_dir():
	headers, response = test('GET', '/testdir')

	#Check headers
	assert headers.get('Location') == '/testdir/'

	#Check resposne
	assert response[0] == 307
	assert response[1] == ''

@with_setup(setup_test_get, teardown_test_get)
def test_get_dir_index_listing():
	headers, response = test('GET', '/testdir/', dir_index=True)

	#Check resposne
	assert response[0] == 200
	assert response[1] == 'magic\n'

@with_setup(setup_test_get, teardown_test_get)
def test_get_no_dir_index_listing():
	try:
		headers, response = test('GET', '/testdir/')
		assert False
	except web.HTTPError as error:
		assert error.code == 403

@with_setup(setup_test_get, teardown_test_get)
def test_get_dir_index_file():
	headers, response = test('GET', '/indexdir/')

	#Check headers
	assert headers.get('Content-Type') == 'text/html'
	assert int(headers.get('Content-Length')) == len(test_string)

	#Check resposne
	assert response[0] == 200
	assert response[1].read() == test_string

def test_get_custom_handler():
	pass

def test_put_file():
	pass

def test_put_dir():
	pass

def test_put_nomodify():
	pass

def test_put_custom_handler():
	pass

def test_put_custom_handler_nomodify():
	pass

def test_delete_file():
	pass

def test_delete_dir():
	pass

def test_delete_nomodify():
	pass

def test_put_custom_handler():
	pass

def test_put_custom_handler_nomodify():
	pass
