import base64

from web import web, auth

import fake


test_realm = "Tests"
test_token = "abcdef"


class TestHandler(auth.AuthHandler):
    realm = test_realm

    def auth_any(self, auth):
        return None

    def do_get(self):
        return 204, ''


class TestBasicHandler(auth.BasicAuthHandler):
    realm = test_realm

    def login(self, user, password):
        return user == password

    def do_get(self):
        return 204, ''


class TestTokenHandler(auth.TokenAuthHandler):
    realm = test_realm

    def token(self, token):
        return token == test_token

    def do_get(self):
        return 204, ''


def test_auth_none():
    request = fake.FakeHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    try:
        request.response.headers, request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Any realm="' + test_realm + '"'
        assert error.code == 401


def test_auth_any():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Any none')

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_basic():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Basic ' + base64.b64encode(b'a:a').decode())

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestBasicHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_basic_fail():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Basic ' + base64.b64encode(b'a:b').decode())

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestBasicHandler)

    try:
        request.response.headers, request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Basic realm="' + test_realm + '"'
        assert error.code == 401


def test_auth_token():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Token ' + test_token)

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestTokenHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_token_fail():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Token fake')

    request = fake.FakeHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TestTokenHandler)

    try:
        request.response.headers, request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Token realm="' + test_realm + '"'
        assert error.code == 401
