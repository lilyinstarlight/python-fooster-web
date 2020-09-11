import collections
import io
import multiprocessing
import time

from fooster.web import web


import mock


test_message = b'More test time!'
test_string = test_message.decode('utf-8')


class MyHandler(web.HTTPHandler):
    reader = True

    def respond(self):
        self.comm['handled'].value = True
        return 200, test_message


class OtherHandler(web.HTTPHandler):
    reader = True

    def respond(self):
        self.comm['handled'].value = True
        return 200, test_message


class SpecialHandler(web.HTTPHandler):
    reader = False

    def respond(self):
        self.comm['waiting'].set()
        self.comm['stop'].wait()

        return 204, ''


class HeaderHandler(web.HTTPHandler):
    def respond(self):
        self.response.headers.set('Test', 'True')

        raise web.HTTPError(402)


class HeaderErrorHandler(web.HTTPErrorHandler):
    def respond(self):
        self.response.headers.set('Test', 'True')

        return 402, b''


class HeaderErrorRaiseHandler(web.HTTPErrorHandler):
    def respond(self):
        self.response.headers.set('Test', 'True')

        raise TypeError()


class IOHandler(web.HTTPHandler):
    def respond(self):
        return 200, io.BytesIO(test_message)


class LengthIOHandler(web.HTTPHandler):
    def respond(self):
        self.response.headers.set('Content-Length', '2')

        return 200, io.BytesIO(test_message)


class SimpleHandler(web.HTTPHandler):
    def respond(self):
        return 200, test_message.decode('utf-8')


class SimpleBytesHandler(web.HTTPHandler):
    def do_get(self):
        return 200, test_message


class BadLengthHandler(web.HTTPHandler):
    def respond(self):
        self.response.headers.set('Content-Length', '2')

        return 200, test_message


class EmptyHandler(web.HTTPHandler):
    def respond(self):
        return 204, ''


class CloseHandler(web.HTTPHandler):
    def respond(self):
        self.request.keepalive = False

        return 204, ''


class NoWriteHandler(web.HTTPHandler):
    def respond(self):
        self.response.write_body = False

        return 200, test_message


class NoWriteBytesHandler(web.HTTPHandler):
    def respond(self):
        self.response.write_body = False

        return 200, io.BytesIO(test_message)


class EvilHandler(web.HTTPHandler):
    def respond(self):
        self.response.headers.set('Content-Length', 'bad')

        return 200, io.BytesIO(test_message)


def run(handler, handler_args=None, comm=None, socket=None, socket_error=False, server=None):
    if not socket:
        socket = mock.MockSocket(error=socket_error)

    if not server:
        http_server = mock.MockHTTPServer()
        server = http_server.info

    request_obj = mock.MockHTTPRequest(socket, ('127.0.0.1', 1337), server, handler=handler, handler_args=handler_args, comm=comm, response=web.HTTPResponse)
    response_obj = request_obj.response

    response_obj.handle()

    value = response_obj.wfile.getvalue()

    response_obj.close()

    # response line comes before firt '\r\n'
    response_line = value.split('\r\n'.encode(web.http_encoding), 1)[0]

    if socket_error:
        body = None
    else:
        # body should happen after '\r\n\r\n' at the end of the HTTP stuff
        body = value.split('\r\n\r\n'.encode(web.http_encoding), 1)[1]

    return response_obj, response_line, response_obj.headers, body


def test_write_lock_wait():
    sync = multiprocessing.get_context(web.start_method).Manager()

    stop = sync.Event()
    waiting = sync.Event()

    my_handled = sync.Value('b', 0)
    other_handled = sync.Value('b', 0)

    # both must have the same server
    server = mock.MockHTTPServer()

    # both handlers should have the same mock resource '/' and should therefore block since the first one is atomic
    special = multiprocessing.get_context(web.start_method).Process(target=run, args=(SpecialHandler,), kwargs={'server': server.info, 'comm': {'stop': stop, 'waiting': waiting}})
    my = multiprocessing.get_context(web.start_method).Process(target=run, args=(MyHandler,), kwargs={'server': server.info, 'comm': {'handled': my_handled}})

    try:
        special.start()

        # wait until the handler is blocking
        waiting.wait(timeout=server.poll_interval + 1)
        print(server.res_lock.resources)

        # make sure it is locked once
        assert server.res_lock.resources['/'][1] == 1

        my.start()

        # wait a bit
        time.sleep(server.poll_interval + 1)

        # make sure that the my process did not handle the request
        assert not my_handled.value
        assert not my.is_alive()
        assert server.res_lock.resources['/'][1] == 1

        # make sure special has been here the whole time
        assert special.is_alive()

        # check for proper skipping when locked
        response, response_line, headers, body = run(OtherHandler, server=server.info, comm={'handled': other_handled})

        assert response.request.skip

        # stop special handler
        stop.set()

        # wait a bit
        time.sleep(server.poll_interval + 1)

        # make sure all process exited
        assert not special.is_alive()

        # make sure we removed the lock
        assert not server.res_lock.resources
    finally:
        # join everything
        stop.set()
        special.join(timeout=server.poll_interval + 1)
        my.join(timeout=server.poll_interval + 1)


def test_write_lock_socket_error():
    sync = multiprocessing.get_context(web.start_method).Manager()

    stop = sync.Event()
    waiting = sync.Event()

    other_handled = sync.Value('b', 0)

    # both must have the same server
    server = mock.MockHTTPServer()

    # both handlers should have the same mock resource '/' and should therefore block since the first one is atomic
    special = multiprocessing.get_context(web.start_method).Process(target=run, args=(SpecialHandler,), kwargs={'server': server.info, 'comm': {'stop': stop, 'waiting': waiting}})

    try:
        special.start()

        # wait until the handler is blocking
        waiting.wait(timeout=server.poll_interval + 1)

        # make sure it is locked once
        assert server.res_lock.resources['/'][1] == 1

        # make sure special has been here the whole time
        assert special.is_alive()

        # check for connection error handling when locked
        response, response_line, headers, body = run(OtherHandler, server=server.info, comm={'handled': other_handled}, socket_error=True)
        assert not other_handled.value
        assert response_line == 'HTTP/1.1 408 Request Timeout'.encode(web.http_encoding)

        assert response.request.skip

        # stop special handler
        stop.set()

        # wait a bit
        time.sleep(server.poll_interval + 1)

        # make sure all process exited
        assert not special.is_alive()

        # make sure we removed the lock
        assert not server.res_lock.resources
    finally:
        # join everything
        stop.set()
        special.join(timeout=server.poll_interval + 1)


def test_http_error():
    response, response_line, headers, body = run(web.DummyHandler, {'error': web.HTTPError(402)})

    assert response_line == 'HTTP/1.1 402 Payment Required'.encode(web.http_encoding)


def test_general_error():
    response, response_line, headers, body = run(web.DummyHandler, {'error': TypeError()})

    assert response_line == 'HTTP/1.1 500 Internal Server Error'.encode(web.http_encoding)


def test_error_headers():
    error_headers = web.HTTPHeaders()
    error_headers.set('Test', 'True')

    response, response_line, headers, body = run(web.DummyHandler, {'error': web.HTTPError(402, headers=error_headers)})

    assert response_line == 'HTTP/1.1 402 Payment Required'.encode(web.http_encoding)

    assert headers.get('Test') == 'True'


def test_headers_clear():
    response, response_line, headers, body = run(HeaderHandler)

    assert headers.get('Test') is None


def test_error_handler():
    server = mock.MockHTTPServer(error_routes=collections.OrderedDict([('400', HeaderErrorHandler), ('500', HeaderErrorHandler)]))

    response, response_line, headers, body = run(web.DummyHandler, {'error': TypeError()}, server=server)

    assert response_line == 'HTTP/1.1 402 Payment Required'.encode(web.http_encoding)

    assert headers.get('Test') == 'True'

    assert body == b''


def test_error_handler_error():
    server = mock.MockHTTPServer(error_routes={'500': HeaderErrorRaiseHandler})

    response, response_line, headers, body = run(web.DummyHandler, {'error': TypeError()}, server=server)

    assert response_line == 'HTTP/1.1 500 Internal Server Error'.encode(web.http_encoding)

    assert headers.get('Test') is None
    assert headers.get('Content-Length') == '28'
    assert headers.get('Server') == web.server_version
    assert headers.get('Date')

    assert body == b'500 - Internal Server Error\n'


def test_response_io():
    response, response_line, headers, body = run(IOHandler)

    assert headers.get('Transfer-Encoding') == 'chunked'
    assert headers.get('Content-Length') is None

    assert body == ('{:x}'.format(len(test_message)) + '\r\n').encode(web.http_encoding) + test_message + '\r\n'.encode(web.http_encoding) + '0\r\n\r\n'.encode(web.http_encoding)


def test_response_io_length():
    response, response_line, headers, body = run(LengthIOHandler)

    assert headers.get('Content-Length') == '2'

    assert body == test_message[0:2]


def test_response_str():
    response, response_line, headers, body = run(SimpleHandler)

    assert headers.get('Content-Length') == str(len(test_message))

    assert body == test_message


def test_response_bytes():
    response, response_line, headers, body = run(SimpleBytesHandler)

    assert headers.get('Content-Length') == str(len(test_message))

    assert body == test_message


def test_response_length():
    response, response_line, headers, body = run(BadLengthHandler)

    assert headers.get('Content-Length') == str(len(test_message))

    assert body == test_message


def test_connection_close():
    response, response_line, headers, body = run(EmptyHandler)

    assert headers.get('Connection') is None

    response, response_line, headers, body = run(CloseHandler)

    assert headers.get('Connection') == 'close'


def test_no_write_io():
    response, response_line, headers, body = run(NoWriteHandler)

    assert response_line == 'HTTP/1.1 200 OK'.encode(web.http_encoding)

    assert body == b''


def test_no_write_bytes():
    response, response_line, headers, body = run(NoWriteBytesHandler)

    assert response_line == 'HTTP/1.1 200 OK'.encode(web.http_encoding)

    assert body == b''


def test_write_error():
    response, response_line, headers, body = run(EvilHandler)

    assert response_line == 'HTTP/1.1 200 OK'.encode(web.http_encoding)

    assert headers.get('Content-Length') == 'bad'

    assert body == b''


def test_write_socket_error():
    response, response_line, headers, body = run(SimpleBytesHandler, socket_error=True)

    assert response_line == b''

    assert body is None
