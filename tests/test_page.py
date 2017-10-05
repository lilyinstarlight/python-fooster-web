from fooster.web import web, page

import mock

import pytest


test_string = 'hello {}'
test_fill = 'world'

test_error = '{message}'


@pytest.fixture(scope='function')
def tmp(tmpdir):
    with tmpdir.join('test.html').open('w') as file:
        file.write(test_string)

    with tmpdir.join('error.html').open('w') as file:
        file.write(test_error)

    return str(tmpdir)


def test_page(tmp):
    class TestHandler(page.PageHandler):
        directory = tmp
        page = 'test.html'

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 200
    assert response[1] == test_string


def test_page_format(tmp):
    class TestHandler(page.PageHandler):
        directory = tmp
        page = 'test.html'

        def format(self, page):
            return test_string.format(test_fill)

    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 200
    assert response[1] == test_string.format(test_fill)


def test_page_new_error():
    assert page.new_error() == {'[0-9]{3}': page.PageErrorHandler}


def test_page_error(tmp):
    class TestHandler(page.PageErrorHandler):
        directory = tmp

        def respond(self):
            self.error = web.HTTPError(500)

            return super().respond()

    request = mock.MockHTTPRequest(None, ('', 0), None, handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    import sys
    sys.stderr.write(repr(response[1]))
    assert response[0] == 500
    assert response[1] == '500 - Internal Server Error\n'


def test_page_error_message(tmp):
    class TestHandler(page.PageErrorHandler):
        directory = tmp

        def respond(self):
            self.error = web.HTTPError(500, message=test_fill, status_message='a')

            return super().respond()

    request = mock.MockHTTPRequest(None, ('', 0), None, handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 500
    assert response[1] == test_fill
