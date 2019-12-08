import json
import urllib.parse

from fooster.web import query

import mock


test_query = {'a': 'b', 'c': 'd', 'ä': ' ', 'f': "'asdfjkl'", 'e': '\\,./;[]_)*&^', '2': ''}
test_encoded = '/?' + urllib.parse.urlencode(test_query)


def test_query_decode():
    class TestHandler(query.QueryHandler):
        def do_get(self):
            return 200, json.dumps(self.request.query)

    server = mock.MockHTTPServer(routes=query.new('/', TestHandler))
    regex, handler = list(server.routes.items())[0]
    groups = regex.match(test_encoded).groupdict()

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', resource=test_encoded, groups=groups, handler=handler)

    response = request.handler.respond()

    assert response[0] == 200
    assert json.loads(response[1]) == test_query


def test_query_handler():
    class TestHandler(query.QueryHandler):
        def do_get(self):
            return 200, json.dumps(self.request.query)

    server = mock.MockHTTPServer(routes={r'/\?(?P<query>.*)': TestHandler})
    regex, handler = list(server.routes.items())[0]
    groups = regex.match(test_encoded).groupdict()

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', resource=test_encoded, groups=groups, handler=handler)

    response = request.handler.respond()

    assert response[0] == 200
    assert json.loads(response[1]) == test_query


def test_query_custom():
    class TestHandler(query.QueryHandler):
        def respond(self):
            self.querystr = self.groups['custom']

            return super().respond()

        def do_get(self):
            return 200, json.dumps(self.request.query)

    server = mock.MockHTTPServer(routes={r'/\?(?P<custom>.*)': TestHandler})
    regex, handler = list(server.routes.items())[0]
    groups = regex.match(test_encoded).groupdict()

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', resource=test_encoded, groups=groups, handler=handler)

    response = request.handler.respond()

    assert response[0] == 200
    assert json.loads(response[1]) == test_query


def test_query_empty():
    class TestHandler(query.QueryHandler):
        def do_get(self):
            return 200, json.dumps(self.request.query)

    server = mock.MockHTTPServer(routes=query.new('/', TestHandler))
    regex, handler = list(server.routes.items())[0]
    groups = regex.match('/?').groupdict()

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', resource='/?', groups=groups, handler=handler)

    response = request.handler.respond()

    assert response[0] == 200
    assert json.loads(response[1]) == {}


def test_query_none():
    class TestHandler(query.QueryHandler):
        def do_get(self):
            return 200, json.dumps(self.request.query)

    server = mock.MockHTTPServer(routes=query.new('/', TestHandler))
    regex, handler = list(server.routes.items())[0]

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=handler)

    response = request.handler.respond()

    assert response[0] == 200
    assert json.loads(response[1]) is None


def test_query_not_found():
    class TestHandler(query.QueryHandler):
        def do_get(self):
            return 200, json.dumps(self.request.query)

    server = mock.MockHTTPServer(routes={r'/\?(?P<custom>.*)': TestHandler})
    regex, handler = list(server.routes.items())[0]
    groups = regex.match(test_encoded).groupdict()

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', resource=test_encoded, groups=groups, handler=handler)

    response = request.handler.respond()

    assert response[0] == 200
    assert json.loads(response[1]) is None
