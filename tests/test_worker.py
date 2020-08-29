import multiprocessing
import os
import time

from fooster.web import web


import mock


def test_worker_shutdown():
    sync = multiprocessing.get_context(web.start_method).Manager()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = 0
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None

    # do it again but this time setting worker_shutdown to -1
    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_handle():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        request = mock.MockHTTPRequest(None, None, None, namespace=server.namespace)

        # add request to selector
        with server.requests_lock:
            request_queue.put((request, False, None, True))

            server.requests.value += 1

        # wait another bit
        time.sleep(server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert server.requests.value == 0
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_handle_exception():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        request = mock.MockHTTPRequest(None, None, None, throw=True, namespace=server.namespace)

        with server.requests_lock:
            request_queue.put((request, False, None, True))

            server.requests.value += 1

        # wait another bit
        time.sleep(server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert server.requests.value == 0
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_keepalive():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        request = mock.MockHTTPRequest(None, None, None, keepalive_number=2, namespace=server.namespace)

        with server.requests_lock:
            request_queue.put((request, True, None, True))

            server.requests.value += 1

        # wait for two polls
        time.sleep(server.poll_interval + server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert server.requests.value == 0
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_unhandled():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        request = mock.MockHTTPRequest(None, None, None, keepalive_number=2, handle=False, namespace=server.namespace)

        with server.requests_lock:
            request_queue.put((request, False, None, True))

            server.requests.value += 1

        # wait for two polls
        time.sleep(server.poll_interval + server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_process():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, requests=1)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        os.write(server.write_fd, b'GET / HTTP/1.1\r\n\r\n')

        # wait a bit
        time.sleep(server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_verify_fail():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, verify=False, requests=1)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        os.write(server.write_fd, b'GET / HTTP/1.1\r\n\r\n')

        # wait a bit
        time.sleep(server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert process.is_alive()

        assert server.namespace.handled == 0
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_process_throw():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, throw=True, requests=1)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        os.write(server.write_fd, b'GET / HTTP/1.1\r\n\r\n')

        # wait a bit
        time.sleep(server.poll_interval + 1)

        assert request_queue.qsize() == 0
        assert process.is_alive()

        assert server.namespace.handled == 1
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None


def test_worker_request_error():
    sync = multiprocessing.get_context(web.start_method).Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, error=True, requests=1)

    process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
    process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        os.write(server.write_fd, b'GET / HTTP/1.1\r\n\r\n')

        # wait a bit
        time.sleep(server.poll_interval + 1)

        assert not process.is_alive()
    finally:
        server.namespace.worker_shutdown = -1
        process.join(timeout=server.poll_interval + 1)
        server.namespace.worker_shutdown = None
