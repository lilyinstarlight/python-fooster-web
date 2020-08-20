import json

from fooster.web import web, json as wjson


import mock

import pytest


test_object = {'1': 1, '2': 2, '3': 3}
test_string = json.dumps(test_object).encode()
test_bad = 'notjson'.encode()


class JSONHandler(wjson.JSONHandler):
    def do_get(self):
        return 200, test_object


class JSONNoneHandler(wjson.JSONHandler):
    def do_get(self):
        return 200, None

    def do_post(self):
        return 200, None


class JSONEmptyHandler(wjson.JSONHandler):
    def do_get(self):
        return 204, None

    def do_post(self):
        return 204, None


class JSONDecodeHandler(wjson.JSONHandler):
    def do_post(self):
        return 200, {'type': str(type(self.request.body))}


class JSONErrorHandler(wjson.JSONErrorHandler):
    def respond(self):
        self.error = web.HTTPError(500)

        return super().respond()


class JSONErrorMessageHandler(wjson.JSONErrorHandler):
    def respond(self):
        self.error = web.HTTPError(500, message=test_object, status_message='a')

        return super().respond()


def test_json_encode():
    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=JSONHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'application/json'

    assert response[0] == 200
    assert response[1] == test_string


def test_json_noencode():
    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=JSONEmptyHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert not headers.get('Content-Type')

    assert response[0] == 204
    assert response[1] == b''


def test_json_decode():
    json_headers = web.HTTPHeaders()
    json_headers.set('Content-Type', 'application/json')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=json_headers, body=test_string, method='POST', handler=JSONDecodeHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'application/json'

    assert response[0] == 200
    assert response[1] == json.dumps({'type': str(type(test_object))}).encode(web.default_encoding)


def test_json_nodecode():
    request = mock.MockHTTPRequest(None, ('', 0), None, body=test_string, method='POST', handler=JSONDecodeHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'application/json'

    assert response[0] == 200
    assert response[1] == json.dumps({'type': str(bytes)}).encode(web.default_encoding)


def test_json_bad_decode():
    json_headers = web.HTTPHeaders()
    json_headers.set('Content-Type', 'application/json')

    request = mock.MockHTTPRequest(None, ('', 0), None, headers=json_headers, body=test_bad, method='POST', handler=JSONNoneHandler)

    with pytest.raises(web.HTTPError) as error:
        request.response.headers, request.handler.respond()

    assert error.value.code == 400


def test_json_new_error():
    assert wjson.new_error() == {'[0-9]{3}': wjson.JSONErrorHandler}


def test_json_error():
    request = mock.MockHTTPRequest(None, ('', 0), None, handler=JSONErrorHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'application/json'

    assert response[0] == 500
    assert response[2] == json.dumps({'error': 500, 'status': web.status_messages[500]}).encode(web.http_encoding)


def test_json_error_message():
    request = mock.MockHTTPRequest(None, ('', 0), None, handler=JSONErrorMessageHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'application/json'

    assert response[0] == 500
    assert response[1] == 'a'
    assert response[2] == test_string
