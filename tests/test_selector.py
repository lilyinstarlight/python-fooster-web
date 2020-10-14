import multiprocessing
import os.path
import socket
import time


from fooster.web import web


import mock

import pytest


@pytest.fixture(scope='function')
def tmp_sock(tmpdir_factory):
    sock_path = os.path.join(str(tmpdir_factory.mktemp('unix')), 'sock')

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen()
    server.setblocking(False)

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(sock_path)

    yield server, client

    client.close()
    server.close()


def test_selector_notify_fail(tmp_sock):
    sync = multiprocessing.get_context(web.start_method).Manager()

    control = mock.MockHTTPServerControl(sync, notify_error=True)
    server = mock.MockHTTPServer(control=control, socket=tmp_sock[0])
    selector = web.HTTPSelector(server.control, server.info)

    try:
        tmp_sock[1].send(b'GET / HTTP/1.1\r\n\r\n')

        # wait a bit
        time.sleep(server.poll_interval + 1)

        assert selector.process.is_alive()
    finally:
        server.control.server_shutdown.value = 1
        selector.process.join(timeout=server.poll_interval + 1)
        server.control.server_shutdown.value = 0
