from fooster.web import web

import mock


test_request = 'GET / HTTP/1.1\r\n' + '\r\n'


def run(request, handler=None, timeout=None, keepalive=True, initial_timeout=None, read_exception=False, close=True, skip=False):
    if not isinstance(request, bytes):
        request = request.encode(web.http_encoding)

    if not handler:
        handler = mock.MockHTTPHandler

    server = mock.MockHTTPServer(routes={'/': handler})

    socket = mock.MockSocket(request)

    request_obj = web.HTTPRequest(socket, ('127.0.0.1', 1337), server, timeout)
    request_obj.response = mock.MockHTTPResponse(socket, ('127.0.0.1', 1337), server, request_obj)

    request_obj.skip = skip

    if read_exception:
        def bad_read(self):
            raise Exception()
        request_obj.rfile.read = bad_read
        request_obj.rfile.readline = bad_read

    request_obj.handle(keepalive, initial_timeout)

    if close:
        request_obj.close()

    return request_obj


def test_initial_timeout():
    request = run('', initial_timeout=5)

    assert request.connection.timeout == 5


def test_timeout():
    request = run(test_request, timeout=8, initial_timeout=5)

    assert request.connection.timeout == 8


def test_read_exception():
    request = run(test_request, timeout=8, initial_timeout=5, read_exception=True)

    assert request.connection.timeout == 5
    assert not request.keepalive


def test_no_request():
    request = run('')

    # if no request, do not keepalive
    assert not request.keepalive


def test_request_too_large():
    # request for 'GET aaaaaaa... HTTP/1.1\r\n' where it's length is one over the maximum line size
    long_request = 'GET ' + 'a' * (web.max_line_size - 4 - 9 - 2 + 1) + ' HTTP/1.1\r\n\r\n'

    request = run(long_request)

    assert request.handler.error.code == 414
    assert not request.keepalive


def test_no_newline():
    request = run(test_request[:-4])

    assert request.handler.error.code == 400
    assert not request.keepalive


def test_bad_request_line():
    request = run('GET /\r\n' + '\r\n')

    assert request.handler.error.code == 400
    assert not request.keepalive


def test_wrong_http_version():
    request = run('GET / HTTP/9000\r\n' + '\r\n')

    assert request.handler.error.code == 505
    assert not request.keepalive


def test_header_too_large():
    # create a header for 'TooLong: aaaaaaa...\r\n' where it's length is one over the maximum line size
    test_header_too_long = 'TooLong: ' + 'a' * (web.max_line_size - 9 - 2 + 1) + '\r\n'
    request = run('GET / HTTP/1.1\r\n' + test_header_too_long + '\r\n')

    assert request.handler.error.code == 431
    assert request.handler.error.status_message == 'TooLong Header Too Large'
    assert not request.keepalive


def test_too_many_headers():
    # create a list of headers '1: test\r\n2: test\r\n...' where the number of them is one over the maximum number of headers
    headers = ''.join(str(i) + ': test\r\n' for i in range(web.max_headers + 1))

    request = run('GET / HTTP/1.1\r\n' + headers + '\r\n')

    assert request.handler.error.code == 431
    assert not request.keepalive


def test_header_no_newline():
    request = run('GET / HTTP/1.1\r\n' + 'Test: header')

    assert request.handler.error.code == 400
    assert not request.keepalive


def test_header_no_colon():
    request = run('GET / HTTP/1.1\r\n' + 'Test header\r\n' + '\r\n')

    assert request.handler.error.code == 400
    assert not request.keepalive


def test_connection_close():
    request = run('GET / HTTP/1.1\r\n' + 'Connection: close\r\n' + '\r\n')

    assert not request.keepalive


def test_handler_not_found():
    request = run('GET /nonexistent HTTP/1.1\r\n' + '\r\n')

    assert request.handler.error.code == 404
    assert request.keepalive


def test_keepalive():
    request = run(test_request)

    assert request.keepalive


def test_no_keepalive():
    request = run(test_request, keepalive=False)

    assert not request.keepalive


def test_handler():
    request = run(test_request, handler=web.HTTPHandler)

    assert isinstance(request.handler, web.HTTPHandler)


def test_read_pipelining():
    request = run('GET / HTTP/1.1\r\n' + '\r\n' + 'GET /nonexistent HTTP/1.1\r\n' + '\r\n', close=False)

    assert request.rfile.read() == b'GET /nonexistent HTTP/1.1\r\n\r\n'

    request.close()


def test_close():
    request = run('GET / HTTP/1.1\r\n' + '\r\n')

    assert request.rfile.closed
    assert request.response.closed


def test_skip():
    request = run('', skip=True)

    try:
        request.keepalive
        assert False
    except AttributeError:
        pass

    try:
        request.headers
        assert False
    except AttributeError:
        pass
