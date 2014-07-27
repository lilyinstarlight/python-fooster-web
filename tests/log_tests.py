import os
import shutil

from web import web

from nose.tools import with_setup

message = 'This is just a test'

def make_log(httpd_log='tmp/httpd.log', access_log='tmp/access.log'):
	return web.HTTPLog(httpd_log, access_log)

def test_log_none():
	log = make_log(None, None)

	assert hasattr(log, 'httpd_log')
	assert hasattr(log.httpd_log, 'write')

	assert hasattr(log, 'access_log')
	assert hasattr(log.access_log, 'write')

def setup_log():
	pass

def teardown_log():
	shutil.rmtree('tmp')

@with_setup(setup_log, teardown_log)
def test_mkdir():
	make_log()

	assert os.path.exists('tmp/')
	assert os.path.exists('tmp/httpd.log')
	assert os.path.exists('tmp/access.log')

@with_setup(setup_log, teardown_log)
def test_message():
	log = make_log()

	log.message(message)
	with open(log.httpd_log.name) as log_file:
		value = log_file.read()

	assert value.endswith(message + '\n')

@with_setup(setup_log, teardown_log)
def test_info():
	log = make_log()

	log.info(message)
	with open(log.httpd_log.name) as log_file:
		value = log_file.read()

	assert value.endswith('INFO: ' + message + '\n')

@with_setup(setup_log, teardown_log)
def test_warn():
	log = make_log()

	log.warn(message)
	with open(log.httpd_log.name) as log_file:
		value = log_file.read()

	assert value.endswith('WARN: ' + message + '\n')

@with_setup(setup_log, teardown_log)
def test_error():
	log = make_log()

	log.error(message)
	with open(log.httpd_log.name) as log_file:
		value = log_file.read()

	assert value.endswith('ERROR: ' + message + '\n')

@with_setup(setup_log, teardown_log)
def test_exception():
	log = make_log()

	try:
		raise Exception()
	except:
		log.exception()
	with open(log.httpd_log.name) as log_file:
		value = log_file.readline()

	assert value.endswith('ERROR: Caught exception:\n')

@with_setup(setup_log, teardown_log)
def test_request():
	log = make_log()

	log.request('localhost', 'GET / HTTP/1.1', '200', '1024', '-', '-')
	with open(log.access_log.name) as log_file:
		value = log_file.read()

	#Test for standard HTTP log format

	assert value.startswith('localhost - - [')
	#Timestamp here
	assert value.endswith('] "GET / HTTP/1.1" 200 1024\n')
