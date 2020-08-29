import multiprocessing
import os
import time

from fooster.web import web


import mock


def test_manager_create():
    sync = multiprocessing.get_context(web.start_method).Manager()

    server = mock.MockHTTPServer(sync=sync)

    server.manager_process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.manager, args=(server,))
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
    sync = multiprocessing.get_context(web.start_method).Manager()

    server = mock.MockHTTPServer(sync=sync)

    server.manager_process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.manager, args=(server,))
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
    sync = multiprocessing.get_context(web.start_method).Manager()

    server = mock.MockHTTPServer(sync=sync)

    server.manager_process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.manager, args=(server,))
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
    sync = multiprocessing.get_context(web.start_method).Manager()

    server = mock.MockHTTPServer(max_queue=None, sync=sync)

    server.manager_process = multiprocessing.get_context(web.start_method).Process(target=web.HTTPServer.manager, args=(server,))
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
