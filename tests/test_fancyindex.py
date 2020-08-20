import html
import json
import os
import time
import urllib.parse

from fooster.web import fancyindex


import mock

import pytest


# a JSON-like template
test_index_template = '{{"dirname":"{dirname}","head":"{head}","precontent":"{precontent}","preindex":"{preindex}","postindex":"{postindex}","postcontent":"{postcontent}","entries":[{entries}]}}'
test_index_entry = '{{"url":"{url}","name":"{name}","size":"{size}","modified":"{modified}"}}'
test_index_entry_join = ','
test_index_content_type = 'application/json'

test_string = 'Fancy indexing is fancy'


def run(method, resource, local, remote='', head='', precontent='', preindex='', postindex='', postcontent='', sortclass=fancyindex.DirEntry):
    handler = list(fancyindex.new(local, remote, modify=False, head=head, precontent=precontent, preindex=preindex, postindex=postindex, postcontent=postcontent, sortclass=sortclass, index_template=test_index_template, index_entry=test_index_entry, index_entry_join=test_index_entry_join, index_content_type=test_index_content_type).values())[0]

    request = mock.MockHTTPRequest(None, ('', 0), None, method=method, resource=resource, groups={'path': resource[len(remote):]}, handler=handler)

    return request.response.headers, request.handler.respond()


def run_contents(resource, local, dirname=None):
    headers, response = run('GET', resource, local)

    # check status
    assert response[0] == 200

    # check headers
    assert headers.get('Content-Type') == 'application/json'

    # check response
    index = json.loads(response[1])

    # test constants
    assert index['dirname'] == html.escape(urllib.parse.unquote(resource))
    assert index['head'] == ''
    assert index['precontent'] == ''
    assert index['preindex'] == ''
    assert index['postindex'] == ''
    assert index['postcontent'] == ''

    # test for accuracy of response
    if not dirname:
        basedir = local
    else:
        basedir = os.path.join(local, dirname)

    dirlist = os.listdir(basedir)
    if resource != '/':
        dirlist.append('..')
    assert len(index['entries']) == len(dirlist)
    for entry in index['entries']:
        if entry['url'].endswith('/'):
            entry['url'] = entry['url'][:-1]
        assert urllib.parse.unquote(entry['url']) in dirlist
        path = os.path.join(basedir, html.unescape(entry['name']))
        if entry['name'].endswith('/'):
            entry['name'] = entry['name'][:-1]
        assert html.unescape(entry['name']) in dirlist
        if os.path.isdir(path):
            assert entry['size'] == fancyindex.human_readable_size(None)
        else:
            assert entry['size'] == fancyindex.human_readable_size(os.path.getsize(path))
        assert entry['modified'] == fancyindex.human_readable_time(time.localtime(os.path.getmtime(path)))


@pytest.fixture(scope='function')
def tmp(tmpdir):
    with tmpdir.join('test').open('w') as file:
        file.write(test_string)
    testdir = tmpdir.mkdir('testdir')
    with testdir.join('magic').open('w') as file:
        pass
    tmp = tmpdir.mkdir('tmp')
    with tmp.join('test').open('w') as file:
        pass
    tmp.mkdir('tmp')
    special_tmp = tmpdir.mkdir('tëst')
    with special_tmp.join('test').open('w') as file:
        pass
    html_tmp = tmpdir.mkdir('<test>')
    with html_tmp.join('test').open('w') as file:
        pass

    case_insensitive = tmpdir.join('TEST').exists()

    if not case_insensitive:
        with tmpdir.join('Test').open('w') as file:
            file.write(test_string)
        capital_tmp = tmpdir.mkdir('Tmp')
        with capital_tmp.join('test').open('w') as file:
            pass

    return {'dir': str(tmpdir), 'case_insensitive': case_insensitive}


def test_fancyindex(tmp):
    run_contents('/', tmp['dir'])


def test_fancyindex_child(tmp):
    run_contents('/testdir/', tmp['dir'], 'testdir')


def test_fancyindex_quoted(tmp):
    run_contents('/tëst/', tmp['dir'], 'tëst')


def test_fancyindex_custom_head(tmp):
    headers, response = run('GET', '/', tmp['dir'], head=test_string)

    # check status
    assert response[0] == 200

    # check response
    index = json.loads(response[1])

    # test constants
    assert index['head'] == test_string
    assert index['precontent'] == ''
    assert index['preindex'] == ''
    assert index['postindex'] == ''
    assert index['postcontent'] == ''


def test_fancyindex_custom_precontent(tmp):
    headers, response = run('GET', '/', tmp['dir'], precontent=test_string)

    # check status
    assert response[0] == 200

    # check response
    index = json.loads(response[1])

    # test constants
    assert index['head'] == ''
    assert index['precontent'] == test_string
    assert index['preindex'] == ''
    assert index['postindex'] == ''
    assert index['postcontent'] == ''


def test_fancyindex_custom_preindex(tmp):
    headers, response = run('GET', '/', tmp['dir'], preindex=test_string)

    # check status
    assert response[0] == 200

    # check response
    index = json.loads(response[1])

    # test constants
    assert index['head'] == ''
    assert index['precontent'] == ''
    assert index['preindex'] == test_string
    assert index['postindex'] == ''
    assert index['postcontent'] == ''


def test_fancyindex_custom_postindex(tmp):
    headers, response = run('GET', '/', tmp['dir'], postindex=test_string)

    # check status
    assert response[0] == 200

    # check response
    index = json.loads(response[1])

    # test constants
    assert index['head'] == ''
    assert index['precontent'] == ''
    assert index['preindex'] == ''
    assert index['postindex'] == test_string
    assert index['postcontent'] == ''


def test_fancyindex_custom_postcontent(tmp):
    headers, response = run('GET', '/', tmp['dir'], postcontent=test_string)

    # check status
    assert response[0] == 200

    # check response
    index = json.loads(response[1])

    # test constants
    assert index['head'] == ''
    assert index['precontent'] == ''
    assert index['preindex'] == ''
    assert index['postindex'] == ''
    assert index['postcontent'] == test_string


def test_sortclass_trailing_slash(tmp):
    sort_obj = fancyindex.DirEntry(tmp['dir'], 'testdir')

    assert sort_obj.filename.endswith('/')


def test_sortclass_repr(tmp):
    sort_obj = fancyindex.DirEntry(tmp['dir'], 'test')

    sort_repr = repr(sort_obj)
    assert 'DirEntry' in sort_repr
    assert repr(tmp['dir']) in sort_repr
    assert repr('test') in sort_repr


def test_sortclass_str(tmp):
    sort_obj = fancyindex.DirEntry(tmp['dir'], 'test')

    assert str(sort_obj) == 'test'

    sort_obj = fancyindex.DirEntry(tmp['dir'], 'testdir')

    assert str(sort_obj) == 'testdir/'


def test_sortclass_eq(tmp):
    sort_obj1 = fancyindex.DirEntry(tmp['dir'], 'test')
    sort_obj2 = fancyindex.DirEntry(tmp['dir'], 'test')

    assert sort_obj1 == sort_obj2

    sort_obj3 = fancyindex.DirEntry(tmp['dir'], 'Test')

    assert not sort_obj1 == sort_obj3

    sort_obj4 = fancyindex.DirEntry(tmp['dir'], 'tmp')
    sort_obj5 = fancyindex.DirEntry(os.path.join(tmp['dir'], 'tmp'), 'tmp')

    assert not sort_obj4 == sort_obj5


def test_sortclass_lt(tmp):
    sort_obj1 = fancyindex.DirEntry(tmp['dir'], 'test')
    sort_obj2 = fancyindex.DirEntry(tmp['dir'], 'test')

    assert not sort_obj1 < sort_obj2

    sort_obj3 = fancyindex.DirEntry(tmp['dir'], 'Test')

    assert sort_obj3 < sort_obj2

    sort_obj4 = fancyindex.DirEntry(tmp['dir'], 'tmp')
    sort_obj5 = fancyindex.DirEntry(os.path.join(tmp['dir'], 'tmp'), 'tmp')

    assert sort_obj4 < sort_obj5

    sort_obj6 = fancyindex.DirEntry(os.path.join(tmp['dir'], 'tmp'), 'test')
    sort_obj7 = fancyindex.DirEntry(os.path.join(tmp['dir'], 'Tmp'), 'test')

    assert sort_obj7 < sort_obj6


def test_list_dir(tmp):
    dirlist = fancyindex.list_dir(tmp['dir'])

    if tmp['case_insensitive']:
        assert len(dirlist) == 6

        assert str(dirlist[0]) == '../'
        assert str(dirlist[1]) == '<test>/'
        assert str(dirlist[2]) == 'testdir/'
        assert str(dirlist[3]) == 'tmp/'
        assert str(dirlist[4]) == 'tëst/'
        assert str(dirlist[5]) == 'test'
    else:
        assert len(dirlist) == 8

        assert str(dirlist[0]) == '../'
        assert str(dirlist[1]) == '<test>/'
        assert str(dirlist[2]) == 'testdir/'
        assert str(dirlist[3]) == 'Tmp/'
        assert str(dirlist[4]) == 'tmp/'
        assert str(dirlist[5]) == 'tëst/'
        assert str(dirlist[6]) == 'Test'
        assert str(dirlist[7]) == 'test'


def test_list_dir_custom_sort(tmp):
    class FairEntry(fancyindex.DirEntry):
        def __lt__(self, other):
            return self.path < other.path

    dirlist = fancyindex.list_dir(tmp['dir'], sortclass=FairEntry)

    if tmp['case_insensitive']:
        assert len(dirlist) == 6

        assert str(dirlist[0]) == '../'
        assert str(dirlist[1]) == '<test>/'
        assert str(dirlist[2]) == 'test'
        assert str(dirlist[3]) == 'testdir/'
        assert str(dirlist[4]) == 'tmp/'
        assert str(dirlist[5]) == 'tëst/'
    else:
        assert len(dirlist) == 8

        assert str(dirlist[0]) == '../'
        assert str(dirlist[1]) == '<test>/'
        assert str(dirlist[2]) == 'Test'
        assert str(dirlist[3]) == 'Tmp/'
        assert str(dirlist[4]) == 'test'
        assert str(dirlist[5]) == 'testdir/'
        assert str(dirlist[6]) == 'tmp/'
        assert str(dirlist[7]) == 'tëst/'


def test_list_dir_root(tmp):
    dirlist = fancyindex.list_dir(tmp['dir'], root=True)

    if tmp['case_insensitive']:
        assert len(dirlist) == 5

        assert str(dirlist[0]) == '<test>/'
        assert str(dirlist[1]) == 'testdir/'
        assert str(dirlist[2]) == 'tmp/'
        assert str(dirlist[3]) == 'tëst/'
        assert str(dirlist[4]) == 'test'
    else:
        assert len(dirlist) == 7

        assert str(dirlist[0]) == '<test>/'
        assert str(dirlist[1]) == 'testdir/'
        assert str(dirlist[2]) == 'Tmp/'
        assert str(dirlist[3]) == 'tmp/'
        assert str(dirlist[4]) == 'tëst/'
        assert str(dirlist[5]) == 'Test'
        assert str(dirlist[6]) == 'test'


def test_human_readable_size():
    units = ['B', 'KiB']

    for i, unit in enumerate(units):
        assert fancyindex.human_readable_size(1024 ** i, units=units) == '1.00 ' + unit

    assert fancyindex.human_readable_size(1024 ** len(units), units=units) == '1024.00 ' + units[-1]

    assert fancyindex.human_readable_size(895, units=units) == '895.00 ' + units[0]
    assert fancyindex.human_readable_size(896, units=units) == '0.88 ' + units[1]

    assert fancyindex.human_readable_size(None) == '-'


def test_human_readable_time():
    assert fancyindex.human_readable_time(time.localtime(0)) == time.strftime('%d-%b-%Y %H:%M {}'.format(time.tzname[0]), time.localtime(0))
