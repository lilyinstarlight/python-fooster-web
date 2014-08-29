import os
import shutil

from web import web

import fake

from nose.tools import with_setup

def setup_server():
	if os.path.exists('tmp'):
		shutil.rmtree('tmp')

	os.mkdir('tmp')

def teardown_server():
	shutil.rmtree('tmp')

@with_setup(setup_server, teardown_server)
def test_init():
	httpd = web.HTTPServer(('localhost', 0), { '/': fake.FakeHTTPHandler }, { '500': fake.FakeHTTPErrorHandler }, log=fake.FakeHTTPLog(None, None))

	assert httpd.server_address

@with_setup(setup_server, teardown_server)
def test_ssl():
	httpsd = web.HTTPServer(('localhost', 0), { '/': fake.FakeHTTPHandler }, keyfile='tests/ssl/ssl.key', certfile='tests/ssl/ssl.crt', log=fake.FakeHTTPLog(None, None))

	assert httpsd.using_ssl

@with_setup(setup_server, teardown_server)
def test_start_stop_close():
	httpd = web.HTTPServer(('localhost', 0), { '/': fake.FakeHTTPHandler }, log=fake.FakeHTTPLog(None, None))

	assert not httpd.is_running()

	httpd.start()

	assert httpd.is_running()

	#Make sure it can be called multiple times with the same result
	httpd.start()

	assert httpd.is_running()

	httpd.stop()

	assert not httpd.is_running()

	#Make sure it can be called multiple times with the same result
	httpd.stop()

	assert not httpd.is_running()

	#Double check that we cleaned up after ourselves
	assert httpd.server_thread == None
	assert httpd.manager_thread == None
	assert httpd.manager_shutdown == False
	assert httpd.worker_threads == None
	assert httpd.worker_shutdown == None

	httpd.start()

	assert httpd.is_running()

	#Make sure it stops the server
	httpd.close()

	assert not httpd.is_running()

	#Double check that we cleaned up after ourselves
	assert httpd.server_thread == None
	assert httpd.manager_thread == None
	assert httpd.manager_shutdown == False
	assert httpd.worker_threads == None
	assert httpd.worker_shutdown == None
