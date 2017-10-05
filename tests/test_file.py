import stat
import os

from fooster.web import web, file

import mock

import pytest


test_string = b'secret test message'


def run(method, resource, local, body='', headers=web.HTTPHeaders(), handler=None, remote='', dir_index=False, modify=False, return_handler=False):
    if not isinstance(body, bytes):
        body = body.encode('utf-8')

    if not handler:
        route = file.new(local, remote, dir_index, modify)

        handler = list(route.values())[0]

        local = handler.local
        remote = handler.remote

    request = mock.MockHTTPRequest(None, ('', 0), None, body=body, headers=headers, method=method, resource=resource, groups=(resource[len(remote):],), handler=handler)

    handler_obj = request.handler

    if return_handler:
        return request.response.headers, handler_obj.respond(), handler_obj
    else:
        return request.response.headers, handler_obj.respond()


@pytest.fixture(scope='function')
def tmp_get(tmpdir):
    with tmpdir.join('test').open('wb') as file:
        file.write(test_string)
    with tmpdir.join('test.txt').open('wb') as file:
        file.write(test_string)
    with tmpdir.join('forbidden').open('wb'):
        pass
    tmpdir.join('forbidden').chmod(stat.S_IWRITE)
    testdir = tmpdir.mkdir('testdir')
    with testdir.join('magic').open('wb'):
        pass
    indexdir = tmpdir.mkdir('indexdir')
    with indexdir.join('index.html').open('wb') as file:
        file.write(test_string)

    return str(tmpdir)


def test_get_file(tmp_get):
    headers, response = run('GET', '/test', tmp_get)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_range(tmp_get):
    range = (2, 6)
    length = range[1] - range[0] + 1

    request_headers = web.HTTPHeaders()
    request_headers.set('Range', 'bytes=' + str(range[0]) + '-' + str(range[1]))
    headers, response = run('GET', '/test', tmp_get, headers=request_headers)

    # check headers
    assert int(headers.get('Content-Length')) == length
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') == 'bytes ' + str(range[0]) + '-' + str(range[1]) + '/' + str(len(test_string))

    # check response
    assert response[0] == 206
    assert response[1].read(length) == test_string[range[0]:range[1] + 1]


def test_get_open_range(tmp_get):
    lower = 2
    length = len(test_string) - lower

    request_headers = web.HTTPHeaders()
    request_headers.set('Range', 'bytes=' + str(lower) + '-')
    headers, response = run('GET', '/test', tmp_get, headers=request_headers)

    # check headers
    assert int(headers.get('Content-Length')) == length
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') == 'bytes ' + str(lower) + '-' + str(len(test_string) - 1) + '/' + str(len(test_string))

    # check response
    assert response[0] == 206
    assert response[1].read(length) == test_string[lower:]


def test_get_bad_range(tmp_get):
    request_headers = web.HTTPHeaders()
    request_headers.set('Range', 'badbytes=0-0')
    headers, response = run('GET', '/test', tmp_get, headers=request_headers)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_extra_range(tmp_get):
    request_headers = web.HTTPHeaders()
    request_headers.set('Range', 'bytes=0-' + str(len(test_string)))
    headers, response = run('GET', '/test', tmp_get, headers=request_headers)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_inverted_range(tmp_get):
    request_headers = web.HTTPHeaders()
    request_headers.set('Range', 'bytes=' + str(len(test_string) - 1) + '-0')
    headers, response = run('GET', '/test', tmp_get, headers=request_headers)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_bad_value_range(tmp_get):
    request_headers = web.HTTPHeaders()
    request_headers.set('Range', 'bytes=a-b')
    headers, response = run('GET', '/test', tmp_get, headers=request_headers)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_mime(tmp_get):
    headers, response = run('GET', '/test.txt', tmp_get)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') == 'text/plain'
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_notfound(tmp_get):
    try:
        headers, response = run('GET', '/nonexistent', tmp_get)
        assert False
    except web.HTTPError as error:
        assert error.code == 404

    try:
        headers, response = run('GET', '/test/', tmp_get)
        assert False
    except web.HTTPError as error:
        assert error.code == 404

    try:
        headers, response = run('GET', '/test/nonexistent', tmp_get)
        assert False
    except web.HTTPError as error:
        assert error.code == 404


def test_get_forbidden(tmp_get):
    try:
        headers, response = run('GET', '/forbidden', tmp_get)
        assert False
    except web.HTTPError as error:
        assert error.code == 403


def test_get_dir(tmp_get):
    headers, response = run('GET', '/testdir', tmp_get)

    # check headers
    assert headers.get('Location') == '/testdir/'

    # check resposne
    assert response[0] == 307
    assert response[1] == ''


def test_get_dir_index_listing(tmp_get):
    headers, response = run('GET', '/testdir/', tmp_get, dir_index=True)

    # check resposne
    assert response[0] == 200
    assert response[1] == 'magic\n'


def test_get_no_dir_index_listing(tmp_get):
    try:
        headers, response = run('GET', '/testdir/', tmp_get)
        assert False
    except web.HTTPError as error:
        assert error.code == 403


def test_get_dir_index_file(tmp_get):
    headers, response = run('GET', '/indexdir/', tmp_get)

    # check headers
    assert headers.get('Content-Type') == 'text/html'
    assert int(headers.get('Content-Length')) == len(test_string)

    # check resposne
    assert response[0] == 200
    assert response[1].read() == test_string


def test_get_backdir(tmp_get):
    headers, response = run('GET', '/testdir/../test', tmp_get)

    # check headers
    assert headers.get('Location') == '/test'

    # check resposne
    assert response[0] == 307
    assert response[1] == ''


def test_get_backdir_filename(tmp_get):
    headers, response, handler = run('GET', '/testdir/../test', tmp_get, return_handler=True)

    assert handler.filename is None


def test_get_backdir_past_remote(tmp_get):
    headers, response, handler = run('GET', '/test2/testdir/../../', tmp_get, remote='/test2', return_handler=True)

    # check headers
    assert headers.get('Location') == '/test2/'

    # check resposne
    assert response[0] == 307
    assert response[1] == ''


def test_get_slash_handling(tmp_get):
    headers, response, handler = run('GET', '/test', tmp_get + '/', remote='/', return_handler=True)

    assert handler.local == tmp_get
    assert handler.remote == ''


def test_get_filename_handling(tmp_get):
    headers, response, handler = run('GET', '/test2/magic', os.path.join(tmp_get, 'testdir/'), remote='/test2/', return_handler=True)

    assert handler.local == os.path.join(tmp_get, 'testdir')
    assert handler.remote == '/test2'
    assert handler.filename == os.path.join(tmp_get, 'testdir', 'magic')


def test_get_custom_handler(tmp_get):
    class MyHandler(file.FileHandler):
        filename = os.path.join(tmp_get, 'test')

    headers, response = run('GET', '/', tmp_get, handler=MyHandler)

    # check headers
    assert int(headers.get('Content-Length')) == len(test_string)
    assert headers.get('Accept-Ranges') == 'bytes'
    assert headers.get('Content-Type') is None
    assert headers.get('Content-Range') is None

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string

    # try dir_index
    class MyHandler(file.FileHandler):
        filename = os.path.join(tmp_get, 'testdir/')
        dir_index = True

    headers, response = run('GET', '/', tmp_get, handler=MyHandler)

    # check resposne
    assert response[0] == 200
    assert response[1] == 'magic\n'

    # try index function
    class MyHandler(file.FileHandler):
        filename = os.path.join(tmp_get, 'testdir/')
        dir_index = True

        def index(self):
            return test_string

    headers, response = run('GET', '/', tmp_get, handler=MyHandler)

    # check resposne
    assert response[0] == 200
    assert response[1] == test_string


@pytest.fixture(scope='function')
def tmp_put(tmpdir):
    with tmpdir.join('exists').open('wb'):
        pass
    with tmpdir.join('forbidden').open('wb'):
        pass
    tmpdir.join('forbidden').chmod(stat.S_IREAD)

    return str(tmpdir)


def test_put_file(tmp_put):
    headers, response = run('PUT', '/test', tmp_put, body=test_string, modify=True)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    headers, response = run('GET', '/test', tmp_put)

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_put_continue(tmp_put):
    expect = web.HTTPHeaders()
    expect.set('Expect', '100-continue')

    headers, response, handler = run('PUT', '/continue', tmp_put, headers=expect, body=test_string, modify=True, return_handler=True)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    # check continue
    assert handler.response.wfile.getvalue() == b'HTTP/1.1 100 Continue\r\n\r\n'

    headers, response = run('GET', '/continue', tmp_put)

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_put_existing_file(tmp_put):
    headers, response = run('PUT', '/exists', tmp_put, body=test_string, modify=True)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    headers, response = run('GET', '/exists', tmp_put)

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_put_forbidden(tmp_put):
    try:
        headers, response = run('PUT', '/forbidden', tmp_put, body=test_string, modify=True)
        assert False
    except web.HTTPError as error:
        assert error.code == 403

    headers, response = run('GET', '/forbidden', tmp_put)

    # check response
    assert response[0] == 200
    assert response[1].read() != test_string


def test_put_dir(tmp_put):
    try:
        run('PUT', '/testdir/', tmp_put, body=test_string, modify=True)
        assert False
    except web.HTTPError as error:
        assert error.code == 403

    headers, response = run('GET', '/testdir/', tmp_put, dir_index=True)

    # check response
    assert response[0] == 200
    assert response[1] == ''


def test_put_nomodify(tmp_put):
    try:
        headers, response = run('PUT', '/test', tmp_put, body=test_string, modify=False)
        assert False
    except web.HTTPError as error:
        assert error.code == 405


def test_put_custom_handler(tmp_put):
    class MyHandler(file.ModifyFileHandler):
        filename = os.path.join(tmp_put, 'test')

    headers, response = run('PUT', '/', tmp_put, body=test_string, handler=MyHandler)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    headers, response = run('GET', '/', tmp_put, handler=MyHandler)

    # check response
    assert response[0] == 200
    assert response[1].read() == test_string


def test_put_custom_handler_nomodify(tmp_put):
    class MyHandler(file.FileHandler):
        filename = os.path.join(tmp_put, 'test')

    try:
        headers, response = run('PUT', '/', tmp_put, body=test_string, handler=MyHandler)
        assert False
    except web.HTTPError as error:
        assert error.code == 405


@pytest.fixture(scope='function')
def tmp_delete(tmpdir):
    with tmpdir.join('test').open('wb'):
        pass
    with tmpdir.join('forbidden').open('wb'):
        pass
    forbiddendir = tmpdir.mkdir('forbiddendir')
    forbiddendir.chmod(stat.S_IREAD)
    testdir = tmpdir.mkdir('testdir')

    return str(tmpdir)


def test_delete_file(tmp_delete):
    headers, response = run('DELETE', '/test', tmp_delete, modify=True)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    try:
        headers, response = run('GET', '/test', tmp_delete)
        assert False
    except web.HTTPError as error:
        assert error.code == 404


def test_delete_nonexistent(tmp_delete):
    try:
        headers, response = run('DELETE', '/nonexistent', tmp_delete, modify=True)
        assert False
    except web.HTTPError as error:
        assert error.code == 404


def test_delete_forbidden(tmp_delete):
    try:
        headers, response = run('DELETE', '/forbiddendir/forbidden', tmp_delete, modify=True)
        assert False
    except web.HTTPError as error:
        assert error.code == 403


def test_delete_dir(tmp_delete):
    headers, response = run('DELETE', '/testdir', tmp_delete, modify=True)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    try:
        headers, response = run('GET', '/testdir', tmp_delete)
        assert False
    except web.HTTPError as error:
        assert error.code == 404


def test_delete_nomodify(tmp_delete):
    try:
        headers, response = run('DELETE', '/test', tmp_delete, modify=False)
        assert False
    except web.HTTPError as error:
        assert error.code == 405


def test_delete_custom_handler(tmp_delete):
    class MyHandler(file.ModifyFileHandler):
        filename = os.path.join(tmp_delete, 'test')

    headers, response = run('DELETE', '/', tmp_delete, handler=MyHandler)

    # check response
    assert response[0] == 204
    assert response[1] == ''

    try:
        headers, response = run('GET', '/', tmp_delete, handler=MyHandler)
        assert False
    except web.HTTPError as error:
        assert error.code == 404


def test_delete_custom_handler_nomodify(tmp_delete):
    class MyHandler(file.FileHandler):
        filename = os.path.join(tmp_delete, 'test')

    try:
        headers, response = run('DELETE', '/', tmp_delete, handler=MyHandler)
        assert False
    except web.HTTPError as error:
        assert error.code == 405


def test_normpath():
    assert file.normpath('/A/B/C/') == '/A/B/C/'


def test_normpath_no_leading_slash():
    assert file.normpath('A/B/C/') == 'A/B/C/'


def test_normpath_no_trailing_slash():
    assert file.normpath('/A/B/C') == '/A/B/C'


def test_normpath_neither_slash():
    assert file.normpath('A/B/C') == 'A/B/C'


def test_normpath_empty_path():
    assert file.normpath('/A//B') == '/A/B'


def test_normpath_single_dots():
    assert file.normpath('/A/./B/') == '/A/B/'


def test_normpath_double_dots():
    assert file.normpath('/A/../B/') == '/B/'


def test_normpath_many_double_dots():
    assert file.normpath('/A/../../../../../B/') == '/B/'


def test_normpath_many_double_dots_no_root():
    assert file.normpath('A/../../../../../B/') == 'B/'


def test_normpath_all_fixes():
    assert file.normpath('/A/./B//C/../../D') == '/A/D'
