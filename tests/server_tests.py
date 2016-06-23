import os
import shutil

from web import web

import fake

from nose.tools import with_setup


def setup_server():
    if os.path.exists('tmp'):
        shutil.rmtree('tmp')

    os.mkdir('tmp')


def teardown_server():
    shutil.rmtree('tmp')


@with_setup(setup_server, teardown_server)
def test_init():
    httpd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler}, {'500': fake.FakeHTTPErrorHandler}, log=fake.FakeHTTPLog(None, None))

    assert httpd.server_address


@with_setup(setup_server, teardown_server)
def test_tls():
    httpsd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler}, keyfile='tests/tls/tls.key', certfile='tests/tls/tls.crt', log=fake.FakeHTTPLog(None, None))

    assert httpsd.using_tls


@with_setup(setup_server, teardown_server)
def test_start_stop_close():
    httpd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler}, log=fake.FakeHTTPLog(None, None))

    assert not httpd.is_running()

    httpd.start()

    assert httpd.is_running()

    # make sure it can be called multiple times with the same result
    httpd.start()

    assert httpd.is_running()

    httpd.stop()

    assert not httpd.is_running()

    # make sure it can be called multiple times with the same result
    httpd.stop()

    assert not httpd.is_running()

    # double check that we cleaned up after ourselves
    assert httpd.server_thread is None
    assert httpd.manager_thread is None
    assert not httpd.manager_shutdown
    assert httpd.worker_threads is None
    assert httpd.worker_shutdown is None

    httpd.start()

    assert httpd.is_running()

    # make sure it stops the server
    httpd.close()

    assert not httpd.is_running()

    # double check that we cleaned up after ourselves
    assert httpd.server_thread is None
    assert httpd.manager_thread is None
    assert not httpd.manager_shutdown
    assert httpd.worker_threads is None
    assert httpd.worker_shutdown is None


def test_process_request():
    httpd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler}, log=fake.FakeHTTPLog(None, None))

    httpd.process_request(fake.FakeSocket(), ('127.0.0.1', 1337))

    assert httpd.request_queue.qsize() == 1
