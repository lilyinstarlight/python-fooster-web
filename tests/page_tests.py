import os
import shutil

from web import page

import fake

from nose.tools import with_setup


test_string = 'hello {}'
test_fill = 'world'


def setup_page():
    if os.path.exists('tmp'):
        shutil.rmtree('tmp')

    os.mkdir('tmp')
    with open('tmp/test.html', 'w') as file:
        file.write(test_string)


def teardown_page():
    shutil.rmtree('tmp')


@with_setup(setup_page, teardown_page)
def test_page():
    class TestHandler(page.PageHandler):
        directory = 'tmp'
        page = 'test.html'

    request = fake.FakeHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'text/html'

    assert response[0] == 200
    assert response[1] == test_string


@with_setup(setup_page, teardown_page)
def test_page_format():
    class TestHandler(page.PageHandler):
        directory = 'tmp'
        page = 'test.html'

        def format(self, page):
            return test_string.format(test_fill)

    request = fake.FakeHTTPRequest(None, ('', 0), None, method='GET', handler=TestHandler)

    headers, response = request.response.headers, request.handler.respond()

    assert headers.get('Content-Type') == 'text/html'

    assert response[0] == 200
    assert response[1] == test_string.format(test_fill)
