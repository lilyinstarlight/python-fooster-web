import base64

from web import web, auth

import fake


class TestHandler(auth.AuthHandler):
    def do_get(self):
        return 204, ''


class TestBasicHandler(auth.BasicAuthHandler):
    def do_get(self):
        return 204, ''

    def login(self, user, password):
        return user == password


def test_auth_none():
    request = fake.FakeHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    try:
        request.response.headers, request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'None'
        assert error.code == 401


def test_auth_any():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'any')

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_basic():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', base64.b64encode(b'a:a').decode())

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestBasicHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_basic_fail():
    class TestHandler(auth.BasicAuthHandler):
        def login(self, user, password):
            return user == password

    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', base64.b64encode(b'a:b').decode())

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestBasicHandler)

    try:
        request.response.headers, request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Basic'
        assert error.code == 401
