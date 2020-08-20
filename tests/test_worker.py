import multiprocessing
import os
import time

from fooster.web import web


import mock


def test_manager_create():
    sync = multiprocessing.Manager()

    server = mock.MockHTTPServer(sync=sync)

    server.manager_process = multiprocessing.Process(target=web.HTTPServer.manager, args=(server,))
    server.manager_process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        assert server.manager_process.is_alive()
        assert server.cur_processes.value == server.num_processes
    finally:
        server.namespace.manager_shutdown = True
        server.manager_process.join(timeout=server.poll_interval + 1)
        server.namespace.manager_shutdown = False


def test_worker_death():
    sync = multiprocessing.Manager()

    server = mock.MockHTTPServer(sync=sync)

    server.manager_process = multiprocessing.Process(target=web.HTTPServer.manager, args=(server,))
    server.manager_process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        num_processes = server.cur_processes.value
        assert num_processes == server.num_processes

        server.namespace.worker_shutdown = 0

        # wait a bit for process to die
        time.sleep(server.poll_interval + 1)

        server.namespace.worker_shutdown = None

        # wait a bit for process restart
        time.sleep(server.poll_interval + 1)

        # make sure the process restarted
        assert server.cur_processes.value == num_processes
    finally:
        server.namespace.manager_shutdown = True
        server.manager_process.join(timeout=server.poll_interval + 1)
        server.namespace.manager_shutdown = False


def test_manager_scaling():
    sync = multiprocessing.Manager()

    server = mock.MockHTTPServer(sync=sync)

    server.manager_process = multiprocessing.Process(target=web.HTTPServer.manager, args=(server,))
    server.manager_process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        for i in range(server.max_queue):
            with server.requests_lock:
                server.requests.value += 1

        # wait a bit for processes start
        time.sleep(server.poll_interval * server.max_processes + 1)

        # just make sure it is spawning some but not too many processes
        num_processes = server.cur_processes.value
        assert num_processes > server.num_processes
        assert num_processes <= server.max_processes

        # mark a task as done
        with server.requests_lock:
            server.requests.value -= 1

        # wait a bit for another poll
        time.sleep(server.poll_interval * server.max_processes + 1)

        # make sure the number didn't go down (and isn't over the max)
        last_processes = num_processes
        num_processes = server.cur_processes.value
        assert num_processes >= last_processes
        assert num_processes <= server.max_processes

        # mark all tasks as done
        with server.requests_lock:
            while server.requests.value > 0:
                server.requests.value -= 1

        # wait a bit for another poll
        time.sleep(server.poll_interval * server.max_processes + 1)

        # make sure the number at least went down
        last_processes = num_processes
        num_processes = server.cur_processes.value
        assert num_processes < last_processes
        assert num_processes >= server.num_processes
    finally:
        server.namespace.manager_shutdown = True
        server.manager_process.join(timeout=server.poll_interval + 1)
        server.namespace.manager_shutdown = False


def test_manager_no_scale():
    sync = multiprocessing.Manager()

    server = mock.MockHTTPServer(max_queue=None, sync=sync)

    server.manager_process = multiprocessing.Process(target=web.HTTPServer.manager, args=(server,))
    server.manager_process.start()

    # wait a bit
    time.sleep(server.poll_interval + 1)

    try:
        assert server.manager_process.is_alive()
        assert server.cur_processes.value == server.num_processes
    finally:
        server.namespace.manager_shutdown = True
        server.manager_process.join(timeout=server.poll_interval + 1)
        server.namespace.manager_shutdown = False


def test_worker_shutdown():
    sync = multiprocessing.Manager()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0))
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
    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, requests=1)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, verify=False, requests=1)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, throw=True, requests=1)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
    sync = multiprocessing.Manager()

    request_queue = sync.Queue()

    server = mock.MockHTTPServer(sync=sync, error=True, requests=1)

    process = multiprocessing.Process(target=web.HTTPServer.worker, args=(server, 0, request_queue))
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
