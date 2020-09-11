import logging
import os.path

from fooster.web import web


import mock


def test_init():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler}, {'500': mock.MockHTTPErrorHandler})

    assert httpd.address


def test_tls():
    tls = os.path.join(os.path.dirname(__file__), 'tls')
    httpsd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler}, keyfile=os.path.join(tls, 'tls.key'), certfile=os.path.join(tls, 'tls.crt'))

    assert httpsd.using_tls


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
    assert not httpd.control.manager_shutdown.value
    assert httpd.control.worker_shutdown.value == -1

    httpd.start()

    assert httpd.is_running()

    # make sure it stops the server
    httpd.close()

    assert not httpd.is_running()

    # double check that we cleaned up after ourselves
    assert not httpd.control.manager_shutdown.value
    assert httpd.control.worker_shutdown.value == -1


def test_start_close():
    httpd = web.HTTPServer(('localhost', 0), {'/': mock.MockHTTPHandler})

    assert not httpd.is_running()

    httpd.start()

    assert httpd.is_running()

    # call stop first
    httpd.stop()

    assert not httpd.is_running()

    # make sure it works
    httpd.close()

    assert not httpd.is_running()


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
