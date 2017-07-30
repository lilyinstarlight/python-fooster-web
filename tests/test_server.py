import os
import queue

from web import web

import fake


def test_init():
    httpd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler}, {'500': fake.FakeHTTPErrorHandler})

    assert httpd.server_address


def test_tls():
    tls = os.path.join(os.path.dirname(__file__), 'tls')
    httpsd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler}, keyfile=os.path.join(tls, 'tls.key'), certfile=os.path.join(tls, 'tls.crt'))

    assert httpsd.using_tls


def test_start_stop_close():
    httpd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler})

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
    assert not httpd.namespace.manager_shutdown
    assert httpd.namespace.worker_shutdown is None

    httpd.start()

    assert httpd.is_running()

    # make sure it stops the server
    httpd.close()

    assert not httpd.is_running()

    # double check that we cleaned up after ourselves
    assert not httpd.namespace.manager_shutdown
    assert httpd.namespace.worker_shutdown is None


def test_process_request():
    httpd = web.HTTPServer(('localhost', 0), {'/': fake.FakeHTTPHandler})

    # simulate worker creating request queue
    httpd.request_queue = queue.Queue()

    httpd.process_request(fake.FakeSocket(), ('127.0.0.1', 1337))

    assert httpd.request_queue.qsize() == 1
