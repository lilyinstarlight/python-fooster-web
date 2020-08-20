from fooster.web import web, page


import mock

import pytest


test_string = 'hello {}'
test_fill = 'world'

test_error = '{message}'


class PageHandler(page.PageHandler):
    directory = ''
    page = 'test.html'


class PageFormatHandler(page.PageHandler):
    directory = ''
    page = 'test.html'

    def format(self, page):
        return test_string.format(test_fill)


class PageErrorHandler(page.PageErrorHandler):
    directory = ''

    def respond(self):
        self.error = web.HTTPError(500)

        return super().respond()


class PageErrorMessageHandler(page.PageErrorHandler):
    directory = ''

    def respond(self):
        self.error = web.HTTPError(500, message=test_fill, status_message='a')

        return super().respond()


@pytest.fixture(scope='function')
def tmp(tmpdir):
    with tmpdir.join('test.html').open('w') as file:
        file.write(test_string)

    with tmpdir.join('error.html').open('w') as file:
        file.write(test_error)

    return str(tmpdir)


def test_page(tmp):
    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=PageHandler)

    request.handler.directory = tmp

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 200
    assert response[1] == test_string


def test_page_format(tmp):
    request = mock.MockHTTPRequest(None, ('', 0), None, method='GET', handler=PageFormatHandler)

    request.handler.directory = tmp

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 200
    assert response[1] == test_string.format(test_fill)


def test_page_new_error():
    assert page.new_error() == {'[0-9]{3}': page.PageErrorHandler}


def test_page_error(tmp):
    request = mock.MockHTTPRequest(None, ('', 0), None, handler=PageErrorHandler)

    request.handler.directory = tmp

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 500
    assert response[2] == '500 - Internal Server Error'


def test_page_error_message(tmp):
    request = mock.MockHTTPRequest(None, ('', 0), None, handler=PageErrorMessageHandler)

    request.handler.directory = tmp

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 500
    assert response[1] == 'a'
    assert response[2] == test_fill
