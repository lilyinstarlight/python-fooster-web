from fooster.web import web

import mock


test_message = b'This is a test message.'
test_response = 'OK'
test_status = 'Befuddled'


class Handler(web.HTTPHandler):
    def do_get(self):
        self.response.headers.set('Test', 'hi')
        return 200, test_response

    def do_put(self):
        return 200, 'Extra OK', self.request.body

    def do_InVaLiD(self):
        return 500, 'Oops'


class NoGetHandler(web.HTTPHandler):
    def do_put(self):
        return 200, self.request.body


def run(method, body='', headers=web.HTTPHeaders(), handler=Handler, handler_args={}, return_response_obj=False):
    if not isinstance(body, bytes):
        body = body.encode('utf-8')

    request = mock.MockHTTPRequest(None, ('', 1337), None, body=body, headers=headers, method=method, handler=handler, handler_args=handler_args)

    handler_obj = request.handler

    if return_response_obj:
        return request.response.headers, handler_obj.respond(), handler_obj.response
    else:
        return request.response.headers, handler_obj.respond()


def test_method():
    headers, response = run('GET')

    # check headers
    assert headers.get('Test') == 'hi'

    # check response
    assert response[0] == 200
    assert response[1] == test_response


def test_no_method():
    try:
        headers, response = run('DELETE')
        assert False
    except web.HTTPError as error:
        # check headers
        allow = error.headers.get('Allow').split(',')
        assert 'OPTIONS' in allow
        assert 'HEAD' in allow
        assert 'GET' in allow
        assert 'PUT' in allow
        assert len(allow) == 4

        # check response
        assert error.code == 405


def test_no_get():
    headers, response = run('OPTIONS', handler=NoGetHandler)

    # check headers
    allow = headers.get('Allow').split(',')
    assert 'OPTIONS' in allow
    assert 'PUT' in allow
    assert len(allow) == 2

    # check response
    assert response[0] == 204


def test_continue():
    request_headers = web.HTTPHeaders()
    request_headers.set('Expect', '100-continue')

    headers, response, response_obj = run('PUT', headers=request_headers, return_response_obj=True)

    # check response_obj
    assert response_obj.wfile.getvalue() == b'HTTP/1.1 100 Continue\r\n\r\n'


def test_check_continue():
    class NoContinueHandler(Handler):
        def check_continue(self):
            raise web.HTTPError(417)

    request_headers = web.HTTPHeaders()
    request_headers.set('Expect', '100-continue')

    try:
        headers, response = run('PUT', headers=request_headers, handler=NoContinueHandler)
        assert False
    except web.HTTPError as error:
        assert error.code == 417


def test_get_body():
    headers, response = run('PUT', body=test_message)

    # check response
    assert response[0] == 200
    assert response[2] == test_message


def test_body_bad_length():
    request_headers = web.HTTPHeaders()
    request_headers.set('Content-Length', 'BadNumber')

    try:
        headers, response = run('PUT', headers=request_headers, body=test_message)
        assert False
    except web.HTTPError as error:
        assert error.code == 400


def test_body_too_large():
    long_body = mock.MockBytes()
    long_body.set_len(web.max_request_size + 1)

    try:
        headers, response = run('PUT', body=long_body)
        assert False
    except web.HTTPError as error:
        assert error.code == 413


def test_body_too_large_continue():
    long_body = mock.MockBytes()
    long_body.set_len(web.max_request_size + 1)

    request_headers = web.HTTPHeaders()
    request_headers.set('Expect', '100-continue')

    try:
        headers, response = run('PUT', body=long_body, headers=request_headers)
        assert False
    except web.HTTPError as error:
        assert error.code == 413


def test_options():
    headers, response = run('OPTIONS')

    # check headers
    allow = headers.get('Allow').split(',')
    assert 'OPTIONS' in allow
    assert 'HEAD' in allow
    assert 'GET' in allow
    assert 'PUT' in allow
    assert len(allow) == 4

    # check response
    assert response[0] == 204
    assert response[1] == ''


def test_head():
    headers, response, response_obj = run('HEAD', return_response_obj=True)

    # check headers
    assert headers.get('Test') == 'hi'

    # check response
    assert response[0] == 200
    assert response[1] == test_response

    # check response_obj
    assert not response_obj.write_body


def test_dummy_handler():
    test_error = Exception()
    try:
        headers, response = run('GET', handler=web.DummyHandler, handler_args={'error': test_error})
        assert False
    except Exception as error:
        assert error is test_error


def test_error_handler():
    test_error = web.HTTPError(102)

    headers, response = run('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

    assert response[0] == test_error.code
    assert response[1] == web.status_messages[test_error.code]
    assert response[2] == str(test_error.code) + ' - ' + web.status_messages[test_error.code] + '\n'


def test_error_handler_status():
    test_error = web.HTTPError(102, status_message=test_status)

    headers, response = run('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

    assert response[0] == test_error.code
    assert response[1] == test_status
    assert response[2] == str(test_error.code) + ' - ' + test_status + '\n'


def test_error_handler_message():
    test_error = web.HTTPError(102, test_message)

    headers, response = run('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

    assert response[0] == test_error.code
    assert response[1] == web.status_messages[test_error.code]
    assert response[2] == test_message


def test_error_handler_status_message():
    test_error = web.HTTPError(102, test_message, status_message=test_status)

    headers, response = run('GET', handler=web.HTTPErrorHandler, handler_args={'error': test_error})

    assert response[0] == test_error.code
    assert response[1] == test_status
    assert response[2] == test_message
