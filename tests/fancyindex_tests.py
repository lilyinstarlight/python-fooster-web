import json
import os
import shutil
import time

from web import web, fancyindex

import fake

from nose.tools import with_setup, nottest

import file_tests

#A JSON-like template
test_index_template = '{{"dirname":"{dirname}","head":"{head}","preindex":"{preindex}","postindex":"{postindex}","postcontent":"{postcontent}","entries":[{entries}]}}'
test_index_entry = '{{"name":"{name}","size":"{size}","modified":"{modified}"}}'
test_index_entry_join = ','

test_string = 'Fancy indexing is fancy'

@nottest
def test(method, resource, local='tmp', remote='', head='', preindex='', postindex='', postcontent='', sortclass=fancyindex.DirEntry):
	handler = list(fancyindex.new(local, remote, False, head, preindex, postindex, postcontent, sortclass, test_index_template, test_index_entry, test_index_entry_join).values())[0]

	request = fake.FakeHTTPRequest(None, ('', 0), None)
	request.method = method.lower()
	request.resource = resource
	response = request.response
	groups = ( resource[len(remote):], )

	handler_obj = handler(request, response, groups)

	return handler_obj.respond()

@nottest
def test_contents(resource, dirname):
	response = test('GET', resource)

	#Check status
	assert response[0] == 200

	#Check response
	index = json.loads(response[1])

	#Test constants
	assert index['dirname'] == resource
	assert index['head'] == ''
	assert index['preindex'] == ''
	assert index['postindex'] == ''
	assert index['postcontent'] == ''

	#Test for accuracy of response
	dirlist = os.listdir(dirname)
	if resource != '/':
		dirlist.append('..')
	assert len(index['entries']) == len(dirlist)
	for entry in index['entries']:
		path = os.path.join(dirname, entry['name'])
		if entry['name'].endswith('/'):
			entry['name'] = entry['name'][:-1]
		assert entry['name'] in dirlist
		if os.path.isdir(path):
			assert entry['size'] == fancyindex.human_readable_size(None)
		else:
			assert entry['size'] == fancyindex.human_readable_size(os.path.getsize(path))
		assert entry['modified'] == fancyindex.human_readable_time(time.localtime(os.path.getmtime(path)))

def setup_fancyindex():
	if os.path.exists('tmp'):
		shutil.rmtree('tmp')

	os.mkdir('tmp')
	with open('tmp/test', 'w') as file:
		file.write(test_string)
	with open('tmp/Test', 'w') as file:
		file.write(test_string)
	os.mkdir('tmp/testdir')
	with open('tmp/testdir/magic', 'w') as file:
		pass
	os.mkdir('tmp/indexdir')
	with open('tmp/indexdir/index.html', 'w') as file:
		file.write(test_string)

def teardown_fancyindex():
	shutil.rmtree('tmp')

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex():
	test_contents('/', 'tmp/')

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_child():
	test_contents('/testdir/', 'tmp/testdir/')

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_head():
	response = test('GET', '/', head=test_string)

	#Check status
	assert response[0] == 200

	#Check response
	index = json.loads(response[1])

	#Test constant
	print(index['head'])
	assert index['head'] == test_string
	assert index['preindex'] == ''
	assert index['postindex'] == ''
	assert index['postcontent'] == ''

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_preindex():
	response = test('GET', '/', preindex=test_string)

	#Check status
	assert response[0] == 200

	#Check response
	index = json.loads(response[1])

	#Test constant
	assert index['head'] == ''
	assert index['preindex'] == test_string
	assert index['postindex'] == ''
	assert index['postcontent'] == ''

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_postindex():
	response = test('GET', '/', postindex=test_string)

	#Check status
	assert response[0] == 200

	#Check response
	index = json.loads(response[1])

	#Test constant
	assert index['head'] == ''
	assert index['preindex'] == ''
	assert index['postindex'] == test_string
	assert index['postcontent'] == ''

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_postcontent():
	response = test('GET', '/', postcontent=test_string)

	#Check status
	assert response[0] == 200

	#Check response
	index = json.loads(response[1])

	#Test constant
	assert index['head'] == ''
	assert index['preindex'] == ''
	assert index['postindex'] == ''
	assert index['postcontent'] == test_string

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
