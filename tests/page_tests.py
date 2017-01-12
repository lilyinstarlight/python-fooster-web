import os
import shutil

from web import page

import fake

import pytest


test_string = 'hello {}'
test_fill = 'world'


@pytest.fixture(scope='function')
def tmp(tmpdir):
    with tmpdir.join('test.html').open('w') as file:
        file.write(test_string)

    return str(tmpdir)


def test_page(tmp):
    class TestHandler(page.PageHandler):
        directory = tmp
        page = 'test.html'

    request = fake.FakeHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

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

    request = fake.FakeHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type').startswith('text/html; charset=')

    assert response[0] == 200
    assert response[1] == test_string.format(test_fill)
