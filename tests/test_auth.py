import base64

from fooster.web import web, auth

import mock


test_header = 'Test'
test_value = 'value'
test_realm = 'Tests'
test_token = 'abcdef'


class Handler(auth.AuthHandler):
    realm = test_realm

    def auth_any(self, auth):
        return None

    def do_get(self):
        return 204, ''


class ErrorHeaderHandler(auth.AuthHandler):
    realm = test_realm

    def auth_any(self, _):
        headers = web.HTTPHeaders()
        headers.set(test_header, test_value)
        raise auth.AuthError(self.scheme, test_realm, headers=headers)

    def do_get(self):
        return 204, ''


class ForbiddenHandler(auth.AuthHandler):
    realm = test_realm

    def forbidden(self):
        return True

    def auth_any(self, auth):
        return None

    def do_get(self):
        return 204, ''


class BasicHandler(auth.BasicAuthHandler):
    realm = test_realm

    def login(self, user, password):
        return user == password

    def do_get(self):
        return 204, ''


class TokenHandler(auth.TokenAuthHandler):
    realm = test_realm

    def token(self, token):
        return token == test_token

    def do_get(self):
        return 204, ''


def test_auth_none():
    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=Handler)

    try:
        request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Any realm="' + test_realm + '"'
        assert error.code == 401


def test_auth_nonexistent():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Nonexistent none')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=Handler)

    try:
        request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Any realm="' + test_realm + '"'
        assert error.code == 401


def test_auth_any():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Any none')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=Handler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_any_error_headers():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Any none')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=ErrorHeaderHandler)

    try:
        request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Any realm="' + test_realm + '"'
        assert error.headers.get(test_header) == test_value
        assert error.code == 401


def test_auth_any_forbidden():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Any none')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=ForbiddenHandler)

    try:
        request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers is None
        assert error.code == 403


def test_auth_basic():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Basic ' + base64.b64encode(b'a:a').decode())

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=BasicHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_basic_fail():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Basic ' + base64.b64encode(b'a:b').decode())

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=BasicHandler)

    try:
        request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Basic realm="' + test_realm + '"'
        assert error.code == 401


def test_auth_token():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Token ' + test_token)

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TokenHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('WWW-Authenticate') is None

    assert response[0] == 204


def test_auth_token_fail():
    request_headers = web.HTTPHeaders()
    request_headers.set('Authorization', 'Token fake')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=request_headers, method='GET', handler=TokenHandler)

    try:
        request.handler.respond()
        assert False
    except web.HTTPError as error:
        assert error.headers.get('WWW-Authenticate') == 'Token realm="' + test_realm + '"'
        assert error.code == 401
