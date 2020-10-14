import io
import json
import os
import ssl

import fooster.web
import fooster.web.file
import fooster.web.fancyindex
import fooster.web.auth
import fooster.web.form
import fooster.web.query

from http.client import HTTPConnection, HTTPSConnection


import pytest


test_message = b'This is a test sentence!'


class RootHandler(fooster.web.HTTPHandler):
    def do_get(self):
        return 200, test_message


class IOHandler(fooster.web.HTTPHandler):
    def do_get(self):
        self.response.headers.set('content-length', str(len(test_message)))
        return 200, io.BytesIO(test_message)


class ChunkedHandler(fooster.web.HTTPHandler):
    def do_get(self):
        # create a multichunked 'aaaaaaa...' message
        return 200, io.BytesIO(test_message + b'a' * (fooster.web.stream_chunk_size) + test_message)


class ExceptionHandler(fooster.web.HTTPHandler):
    def do_get(self):
        raise Exception()


string = b''


class EchoHandler(fooster.web.HTTPHandler):
    def do_get(self):
        global string

        return 200, string

    def do_put(self):
        global string

        string = self.request.body

        return 204, ''


saved = {}


class AuthHandler(fooster.web.auth.AuthHandler):
    realm = 'Test'

    def auth_any(self, token):
        return None

    def do_get(self):
        try:
            return 200, saved[self.groups[0]]
        except KeyError:
            raise fooster.web.HTTPError(404)

    def do_put(self):
        saved[self.groups[0]] = self.request.body

        return 200, 'Accepted'


form = None


class FormHandler(fooster.web.form.FormHandler):
    def do_get(self):
        try:
            return 200, json.dumps(form)
        except KeyError:
            raise fooster.web.HTTPError(404)

    def do_post(self):
        form = self.request.body

        return 200, json.dumps(form)


class QueryHandler(fooster.web.query.QueryHandler):
    def do_get(self):
        try:
            return 200, json.dumps(self.request.query)
        except KeyError:
            raise fooster.web.HTTPError(404)


paths = {}


class PathHandler(fooster.web.HTTPHandler):
    def do_get(self):
        try:
            return 200, paths[self.groups['path']]
        except KeyError:
            raise fooster.web.HTTPError(404)

    def do_put(self):
        paths[self.groups['path']] = self.request.body

        return 200, 'Accepted'

    def do_delete(self):
        try:
            del paths[self.groups[0]]
        except KeyError:
            raise fooster.web.HTTPError(404)

        return 200, 'Deleted'


error_message = b'Oh noes, there was an error!'


class ErrorHandler(fooster.web.HTTPErrorHandler):
    def respond(self):
        return 203, error_message


@pytest.fixture(scope='function')
def routes(tmpdir):
    tmp = str(tmpdir)

    routes = {'/': RootHandler, '/io': IOHandler, '/chunked': ChunkedHandler, '/error': ExceptionHandler, '/echo': EchoHandler, '/auth/(.*)': AuthHandler, '/form': FormHandler, '/path/(?P<path>.*)': PathHandler}

    routes.update(fooster.web.file.new(tmp, '/tmpro', dir_index=False, modify=False))
    routes.update(fooster.web.file.new(tmp, '/tmp', dir_index=True, modify=True))

    routes.update(fooster.web.fancyindex.new(tmp, '/tmpfancy'))

    routes.update(fooster.web.query.new('/query', QueryHandler))

    return routes


def run_conn(conn):
    # test_root
    conn.request('GET', '/')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    # test_io
    conn.request('GET', '/io')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    # test_chunked
    conn.request('GET', '/chunked')
    response = conn.getresponse()
    assert response.status == 200
    assert response.getheader('Transfer-Encoding') == 'chunked'
    text = response.read()
    assert text.startswith(test_message)
    assert text[len(test_message)] == ord(b'a')
    assert text.endswith(test_message)

    # test_error
    conn.request('GET', '/error')
    response = conn.getresponse()
    assert response.status == 203
    assert response.read() == error_message

    # test_echo
    conn.request('GET', '/echo')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == string

    conn.request('PUT', '/echo', test_message)
    response = conn.getresponse()
    assert response.status == 204
    assert response.read() == b''

    conn.request('GET', '/echo')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    # test_auth
    conn.request('GET', '/auth/')
    response = conn.getresponse()
    assert response.status == 401
    assert response.getheader('WWW-Authenticate') == 'Any realm="Test"'
    response.read()

    conn.request('GET', '/auth/', headers={'Authorization': 'Any None'})
    response = conn.getresponse()
    assert response.status == 404
    response.read()

    conn.request('PUT', '/auth/test', test_message, headers={'Authorization': 'Any None'})
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == b'Accepted'

    conn.request('GET', '/auth/test', headers={'Authorization': 'Any None'})
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    # test_form
    conn.request('GET', '/form')
    response = conn.getresponse()
    assert response.status == 200
    assert json.loads(response.read().decode()) is None

    conn.request('POST', '/form', 'test&test2=test3', headers={'Content-Type': 'application/x-www-form-urlencoded'})
    response = conn.getresponse()
    assert response.status == 200
    assert json.loads(response.read().decode()) == {'test': '', 'test2': 'test3'}

    conn.request('POST', '/form', b'--asdf\r\nContent-Disposition: form-data; name="test"\r\n\r\n\r\n--asdf\r\nContent-Disposition: form-data; name="test2"\r\n\r\ntest3\r\n--asdf--\r\n', headers={'Content-Type': 'multipart/form-data; boundary=asdf'})
    response = conn.getresponse()
    assert response.status == 200
    assert json.loads(response.read().decode()) == {'test': '', 'test2': 'test3'}

    # test_query
    conn.request('GET', '/query')
    response = conn.getresponse()
    assert response.status == 200
    assert json.loads(response.read().decode()) is None

    conn.request('GET', '/query?')
    response = conn.getresponse()
    assert response.status == 200
    assert json.loads(response.read().decode()) == {}

    conn.request('GET', '/query?test&test2=test3')
    response = conn.getresponse()
    assert response.status == 200
    assert json.loads(response.read().decode()) == {'test': '', 'test2': 'test3'}

    # test_path
    conn.request('GET', '/path/')
    response = conn.getresponse()
    assert response.status == 404
    response.read()

    conn.request('PUT', '/path/test', test_message)
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == b'Accepted'

    conn.request('GET', '/path/test')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    # test_file_tmp
    conn.request('GET', '/tmp/')
    response = conn.getresponse()
    assert response.status == 200
    response.read()

    conn.request('GET', '/tmp/test')
    response = conn.getresponse()
    assert response.status == 404
    response.read()

    conn.request('PUT', '/tmp/test', test_message)
    response = conn.getresponse()
    assert response.status == 204
    assert response.read() == b''

    conn.request('GET', '/tmp/test')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    # test_file_tmp_ro
    conn.request('GET', '/tmpro/')
    response = conn.getresponse()
    assert response.status == 403
    response.read()

    conn.request('GET', '/tmpro/test')
    response = conn.getresponse()
    assert response.status == 200
    assert response.read() == test_message

    conn.request('PUT', '/tmpro/test')
    response = conn.getresponse()
    assert response.status == 405
    response.read()

    # test_file_delete
    conn.request('DELETE', '/tmp/test')
    response = conn.getresponse()
    assert response.status == 204
    assert response.read() == b''

    # test_fancyindex_tmp
    conn.request('GET', '/tmpfancy/')
    response = conn.getresponse()
    assert response.status == 200
    response.read()

    # test_close
    # close the connection since this is our last request
    conn.request('GET', '/', headers={'Connection': 'close'})
    response = conn.getresponse()
    assert response.status == 200
    response.read()


def test_integration_http(routes):
    # create
    httpd = fooster.web.HTTPServer(('localhost', 0), routes, {'500': ErrorHandler})

    # start
    httpd.start()

    # test_running
    assert httpd.is_running()

    # test
    try:
        run_conn(HTTPConnection('localhost', httpd.address[1]))
    # close
    finally:
        httpd.close()


@pytest.mark.skip()
def test_integration_https(routes):
    # create
    tls = os.path.join(os.path.dirname(__file__), 'tls')
    httpsd = fooster.web.HTTPServer(('localhost', 0), routes, {'500': ErrorHandler}, keyfile=os.path.join(tls, 'tls.key'), certfile=os.path.join(tls, 'tls.crt'))

    # start
    httpsd.start()

    # test_running
    assert httpsd.is_running()

    # test
    try:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except AttributeError:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cafile=os.path.join(tls, 'tls.crt'))

        run_conn(HTTPSConnection('localhost', httpsd.address[1], context=context))
    # close
    finally:
        httpsd.close()
