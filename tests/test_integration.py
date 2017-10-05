#import io
#import os
#import ssl
#
#import fooster.web
#import fooster.web.file
#import fooster.web.fancyindex
#
#from http.client import HTTPConnection, HTTPSConnection
#
#import pytest
#
#
#test_message = b'This is a test sentence!'
#
#
#class RootHandler(fooster.web.HTTPHandler):
#    def do_get(self):
#        return 200, test_message
#
#
#class IOHandler(fooster.web.HTTPHandler):
#    def do_get(self):
#        self.response.headers.set('content-length', str(len(test_message)))
#        return 200, io.BytesIO(test_message)
#
#
#class ChunkedHandler(fooster.web.HTTPHandler):
#    def do_get(self):
#        # create a multichunked 'aaaaaaa...' message
#        return 200, io.BytesIO(test_message + b'a' * (fooster.web.stream_chunk_size) + test_message)
#
#
#class ExceptionHandler(fooster.web.HTTPHandler):
#    def do_get(self):
#        raise Exception()
#
#
#string = b''
#
#
#class EchoHandler(fooster.web.HTTPHandler):
#    def do_get(self):
#        global string
#
#        return 200, string
#
#    def do_put(self):
#        global string
#
#        string = self.request.body
#
#        return 204, ''
#
#
#saved = {}
#
#
#class AuthHandler(fooster.web.HTTPHandler):
#    def do_get(self):
#        if not self.request.headers.get('Authorization'):
#            auth_headers = fooster.web.HTTPHeaders()
#            auth_headers.set('WWW-Authenticate', 'Any')
#            raise fooster.web.HTTPError(401, headers=auth_headers)
#
#        try:
#            return 200, saved[self.groups[0]]
#        except KeyError:
#            raise fooster.web.HTTPError(404)
#
#    def do_put(self):
#        saved[self.groups[0]] = self.request.body
#
#        return 200, 'Accepted'
#
#
#error_message = b'Oh noes, there was an error!'
#
#
#class ErrorHandler(fooster.web.HTTPErrorHandler):
#    def respond(self):
#        return 203, error_message
#
#
#@pytest.fixture(scope='function')
#def routes(tmpdir):
#    tmp = str(tmpdir)
#
#    routes = {'/': RootHandler, '/io': IOHandler, '/chunked': ChunkedHandler, '/error': ExceptionHandler, '/echo': EchoHandler, '/auth/(.*)': AuthHandler}
#
#    routes.update(fooster.web.file.new(tmp, '/tmpro', dir_index=False, modify=False))
#    routes.update(fooster.web.file.new(tmp, '/tmp', dir_index=True, modify=True))
#
#    routes.update(fooster.web.fancyindex.new(tmp, '/tmpfancy'))
#
#    return routes
#
#
#@pytest.fixture(scope='function')
#def tmp(tmpdir):
#    return str(tmpdir)
#
#
#def test_integration_http(routes, tmp):
#    # create
#    httpd = fooster.web.HTTPServer(('localhost', 0), routes, {'500': ErrorHandler})
#
#    # start
#    httpd.start()
#
#    # test_running
#    assert httpd.is_running()
#
#    # test
#    try:
#        run_conn(HTTPConnection('localhost', httpd.server_address[1]))
#    # close
#    finally:
#        httpd.close()
#
#
#def test_integration_https(routes, tmp):
#    # create
#    tls = os.path.join(os.path.dirname(__file__), 'tls')
#    httpsd = fooster.web.HTTPServer(('localhost', 0), routes, {'500': ErrorHandler}, keyfile=os.path.join(tls, 'tls.key'), certfile=os.path.join(tls, 'tls.crt'))
#
#    # start
#    httpsd.start()
#
#    # test_running
#    assert httpsd.is_running()
#
#    # test
#    try:
#        context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
#        context.verify_mode = ssl.CERT_REQUIRED
#        context.load_verify_locations(cafile=os.path.join(tls, 'tls.crt'))
#
#        run_conn(HTTPSConnection('localhost', httpsd.server_address[1], context=context))
#    # close
#    finally:
#        httpsd.close()
#
#
#def run_conn(conn):
#    # test_root
#    conn.request('GET', '/')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == test_message
#
#    # test_io
#    conn.request('GET', '/io')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == test_message
#
#    # test_chunked
#    conn.request('GET', '/chunked')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.getheader('Transfer-Encoding') == 'chunked'
#    text = response.read()
#    assert text.startswith(test_message)
#    assert text[len(test_message)] == ord(b'a')
#    assert text.endswith(test_message)
#
#    # test_error
#    conn.request('GET', '/error')
#    response = conn.getresponse()
#    assert response.status == 203
#    assert response.read() == error_message
#
#    # test_echo
#    conn.request('GET', '/echo')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == string
#
#    conn.request('PUT', '/echo', test_message)
#    response = conn.getresponse()
#    assert response.status == 204
#    assert response.read() == b''
#
#    conn.request('GET', '/echo')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == test_message
#
#    # test_auth
#    conn.request('GET', '/auth/')
#    response = conn.getresponse()
#    assert response.status == 401
#    assert response.getheader('WWW-Authenticate') == 'Any'
#    response.read()
#
#    conn.request('GET', '/auth/', headers={'Authorization': 'None'})
#    response = conn.getresponse()
#    assert response.status == 404
#    response.read()
#
#    conn.request('PUT', '/auth/test', test_message)
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == b'Accepted'
#
#    conn.request('GET', '/auth/test', headers={'Authorization': 'None'})
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == test_message
#
#    # test_file_tmp
#    conn.request('GET', '/tmp/')
#    response = conn.getresponse()
#    assert response.status == 200
#    response.read()
#
#    conn.request('GET', '/tmp/test')
#    response = conn.getresponse()
#    assert response.status == 404
#    response.read()
#
#    conn.request('PUT', '/tmp/test', test_message)
#    response = conn.getresponse()
#    assert response.status == 204
#    assert response.read() == b''
#
#    conn.request('GET', '/tmp/test')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == test_message
#
#    # test_file_tmp_ro
#    conn.request('GET', '/tmpro/')
#    response = conn.getresponse()
#    assert response.status == 403
#    response.read()
#
#    conn.request('GET', '/tmpro/test')
#    response = conn.getresponse()
#    assert response.status == 200
#    assert response.read() == test_message
#
#    conn.request('PUT', '/tmpro/test')
#    response = conn.getresponse()
#    assert response.status == 405
#    response.read()
#
#    # test_file_delete
#    conn.request('DELETE', '/tmp/test')
#    response = conn.getresponse()
#    assert response.status == 204
#    assert response.read() == b''
#
#    # test_fancyindex_tmp
#    conn.request('GET', '/tmpfancy/')
#    response = conn.getresponse()
#    assert response.status == 200
#    response.read()
#
#    # test_close
#    # close the connection since this is our last request
#    conn.request('GET', '/', headers={'Connection': 'close'})
#    response = conn.getresponse()
#    assert response.status == 200
#    response.read()
