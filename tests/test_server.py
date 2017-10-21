import logging
import multiprocessing
import os
import queue

from fooster.web import web

import mock


def test_init():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler}, {'500': mock.MockHTTPErrorHandler})

    assert httpd.server_address


def test_tls():
    tls = os.path.join(os.path.dirname(__file__), 'tls')
    httpsd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler}, keyfile=os.path.join(tls, 'tls.key'), certfile=os.path.join(tls, 'tls.crt'))

    assert httpsd.using_tls


def test_sync():
    sync = multiprocessing.Manager()

    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler}, sync=sync)

    assert httpd.sync is sync


def test_log():
    log = logging.getLogger('test')
    http_log = logging.getLogger('test_http')

    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler}, log=log, http_log=http_log)

    assert httpd.log is log
    assert httpd.http_log is http_log


def test_start_stop_close():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler})

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


def test_start_shutdown_join():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler})

    assert not httpd.is_running()

    httpd.start()

    assert httpd.is_running()

    # make sure it can be called multiple times with the same result
    httpd.start()

    assert httpd.is_running()

    httpd.join(1)

    assert httpd.is_running()

    httpd.shutdown()

    httpd.join()

    assert not httpd.is_running()

    httpd.join()

    httpd.stop()


def test_process_request():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler})

    # simulate worker creating request queue
    httpd.request_queue = queue.Queue()

    httpd.process_request(mock.MockSocket(), ('127.0.0.1', 1337))

    assert httpd.request_queue.qsize() == 1

def test_handle_error():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler})

    httpd.handle_error(None, None)
