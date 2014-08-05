import json
import os
import shutil
import time

from web import web, fancyindex

import fake

from nose.tools import with_setup, nottest

import file_tests

#A JSON-like template
test_index_template = '{{"dirname":"{dirname}","head":"{head}","precontent":"{precontent}","preindex":"{preindex}","postindex":"{postindex}","postcontent":"{postcontent}","entries":[{entries}]}}'
test_index_entry = '{{"name":"{name}","size":"{size}","modified":"{modified}"}}'
test_index_entry_join = ','

test_string = 'Fancy indexing is fancy'

@nottest
def test(method, resource, local='tmp', remote='', head='', precontent='', preindex='', postindex='', postcontent='', sortclass=fancyindex.DirEntry):
	handler = list(fancyindex.new(local, remote, False, head, precontent, preindex, postindex, postcontent, sortclass, test_index_template, test_index_entry, test_index_entry_join).values())[0]

	request = fake.FakeHTTPRequest(None, ('', 0), None, method=method, resource=resource, groups=(resource[len(remote):],), handler=handler)

	return request.handler.respond()

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
	assert index['precontent'] == ''
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
	os.mkdir('tmp/tmp')
	with open('tmp/tmp/test', 'w') as file:
		pass
	os.mkdir('tmp/Tmp')
	with open('tmp/Tmp/test', 'w') as file:
		pass

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

	#Test constants
	assert index['head'] == test_string
	assert index['precontent'] == ''
	assert index['preindex'] == ''
	assert index['postindex'] == ''
	assert index['postcontent'] == ''

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_fancyindex_custom_precontent():
	response = test('GET', '/', precontent=test_string)

	#Check status
	assert response[0] == 200

	#Check response
	index = json.loads(response[1])

	#Test constants
	assert index['head'] == ''
	assert index['precontent'] == test_string
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

	#Test constants
	assert index['head'] == ''
	assert index['precontent'] == ''
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

	#Test constants
	assert index['head'] == ''
	assert index['precontent'] == ''
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

	#Test constants
	assert index['head'] == ''
	assert index['precontent'] == ''
	assert index['preindex'] == ''
	assert index['postindex'] == ''
	assert index['postcontent'] == test_string

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_sortclass_trailing_slash():
	sort_obj = fancyindex.DirEntry('tmp/', 'testdir')

	assert sort_obj.filename.endswith('/')

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_sortclass_repr():
	sort_obj = fancyindex.DirEntry('tmp/', 'test')

	sort_repr = repr(sort_obj)
	assert 'DirEntry' in sort_repr
	assert 'tmp/' in sort_repr
	assert 'test' in sort_repr

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_sortclass_str():
	sort_obj = fancyindex.DirEntry('tmp/', 'test')

	assert str(sort_obj) == 'test'

	sort_obj = fancyindex.DirEntry('tmp/', 'testdir')

	assert str(sort_obj) == 'testdir/'

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_sortclass_eq():
	sort_obj1 = fancyindex.DirEntry('tmp/', 'test')
	sort_obj2 = fancyindex.DirEntry('tmp/', 'test')

	assert sort_obj1 == sort_obj2

	sort_obj3 = fancyindex.DirEntry('tmp/', 'Test')

	assert not sort_obj1 == sort_obj3

	sort_obj4 = fancyindex.DirEntry('./', 'tmp')
	sort_obj5 = fancyindex.DirEntry('tmp/', 'tmp')

	assert not sort_obj4 == sort_obj5

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_sortclass_lt():
	sort_obj1 = fancyindex.DirEntry('tmp/', 'test')
	sort_obj2 = fancyindex.DirEntry('tmp/', 'test')

	assert not sort_obj1 < sort_obj2

	sort_obj3 = fancyindex.DirEntry('tmp/', 'Test')

	assert sort_obj3 < sort_obj2

	sort_obj4 = fancyindex.DirEntry('./', 'tmp')
	sort_obj5 = fancyindex.DirEntry('tmp/', 'tmp')

	assert sort_obj4 < sort_obj5

	sort_obj6 = fancyindex.DirEntry('tmp/tmp/', 'test')
	sort_obj7 = fancyindex.DirEntry('tmp/Tmp/', 'test')

	assert sort_obj7 < sort_obj6

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_listdir():
	dirlist = fancyindex.listdir('tmp/')

	assert len(dirlist) == 6

	assert str(dirlist[0]) == '../'
	assert str(dirlist[1]) == 'testdir/'
	assert str(dirlist[2]) == 'Tmp/'
	assert str(dirlist[3]) == 'tmp/'
	assert str(dirlist[4]) == 'Test'
	assert str(dirlist[5]) == 'test'

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_listdir_custom_sort():
	class FairEntry(fancyindex.DirEntry):
		def __lt__(self, other):
			return self.path < other.path

	dirlist = fancyindex.listdir('tmp/', sortclass=FairEntry)

	assert len(dirlist) == 6

	assert str(dirlist[0]) == '../'
	assert str(dirlist[1]) == 'Test'
	assert str(dirlist[2]) == 'Tmp/'
	assert str(dirlist[3]) == 'test'
	assert str(dirlist[4]) == 'testdir/'
	assert str(dirlist[5]) == 'tmp/'

@with_setup(setup_fancyindex, teardown_fancyindex)
def test_listdir_root():
	dirlist = fancyindex.listdir('tmp/', root=True)

	assert len(dirlist) == 5

	assert str(dirlist[0]) == 'testdir/'
	assert str(dirlist[1]) == 'Tmp/'
	assert str(dirlist[2]) == 'tmp/'
	assert str(dirlist[3]) == 'Test'
	assert str(dirlist[4]) == 'test'

def test_human_readable_size():
	units = [ 'B', 'KiB' ]

	for i, unit in enumerate(units):
		assert fancyindex.human_readable_size(1024 ** i, units=units) == '1.00 ' + unit

	assert fancyindex.human_readable_size(1024 ** len(units), units=units) == '1024.00 ' + units[-1]

	assert fancyindex.human_readable_size(895, units=units) == '895.00 ' + units[0]
	assert fancyindex.human_readable_size(896, units=units) == '0.88 ' + units[1]

	assert fancyindex.human_readable_size(None) == '-'

def test_human_readable_time():
	assert fancyindex.human_readable_time(time.gmtime(0)) == '01-Jan-1970 00:00 GMT'
