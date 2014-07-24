import os
import shutil

from web import web, fancyindex

from nose.tools import with_setup, nottest

import file_tests

#Specify custom template that is easy to parse for error checking

test_string = b'Fancy indexing is fancy'

@nottest
def test(method, resource, body='', headers=web.HTTPHeaders(), handler=None, local='tmp', remote='', modify=False):
	if not handler:
		handler = list(fancyindex.new(local, remote, modify).values())[0]

	return file_tests.test(method, resource, body, headers, handler, local, remote, True, modify)

def setup_fancyindex():
	if os.path.exists('tmp'):
		shutil.rmtree('tmp')

	os.mkdir('tmp')
	with open('tmp/test', 'wb') as file:
		file.write(test_string)
	with open('tmp/Test', 'wb') as file:
		file.write(test_string)
	os.mkdir('tmp/testdir')
	with open('tmp/testdir/magic', 'wb') as file:
		pass
	os.mkdir('tmp/indexdir')
	with open('tmp/indexdir/index.html', 'wb') as file:
		file.write(test_string)

def teardown_fancyindex():
	shutil.rmtree('tmp')

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex():
	test('GET', '/')

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_head():
	pass

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_preindex():
	pass

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_postindex():
	pass

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_postcontent():
	pass

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_parent():
	pass

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_root():
	pass

def test_sortclass_trailing_slash():
	pass

def test_sortclass_repr():
	pass

def test_sortclass_str():
	pass

def test_sortclass_eq():
	pass

def test_sortclass_lt():
	pass

def test_listdir():
	pass

def test_listdir_custom_sort():
	pass

def test_listdir_root():
	pass

def test_human_readable_size():
	pass

def test_human_readable_time():
	pass
