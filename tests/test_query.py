import urllib.parse

from fooster.web import web, query

import mock


test_query = {'a': 'b', 'c': 'd', 'ä': ' ', 'f': "'asdfjkl'", 'e': '\,./;[]_)*&^', '2': ''}
test_encoded = '/?' + urllib.parse.urlencode(test_query)


def test_query_decode():
    class TestHandler(web.HTTPHandler):
        def do_get(self):
            return 200, repr(self.request.query)

    server = mock.MockHTTPServer(routes=query.new('/', TestHandler))
    regex, handler = list(server.routes.items())[0]
    groups = regex.match(test_encoded).groups()

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', resource=test_encoded, groups=groups, handler=handler)

    headers, response = request.response.headers, request.handler.respond()

    assert response[0] == 200
    assert eval(response[1]) == test_query
