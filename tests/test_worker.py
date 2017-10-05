#import threading
#import time
#
#from fooster.web import web
#
#import mock
#
#
#def test_manager_create_threads():
#    server = mock.MockHTTPServer()
#
#    server.manager_thread = threading.Thread(target=web.HTTPServer.manager, args=(server,))
#    server.manager_thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    assert len(server.worker_threads) == server.num_threads
#    for thread in server.worker_threads:
#        assert thread.is_alive()
#
#    server.manager_shutdown = True
#    server.manager_thread.join(timeout=1)
#    server.manager_shutdown = False
#
#    assert server.worker_threads is None
#
#
#def test_manager_thread_death():
#    server = mock.MockHTTPServer()
#
#    server.manager_thread = threading.Thread(target=web.HTTPServer.manager, args=(server,))
#    server.manager_thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    server.worker_shutdown = 0
#    server.worker_threads[0].join(timeout=1)
#    server.worker_shutdown = None
#
#    # wait a bit for thread restart
#    time.sleep(server.poll_interval + 0.1)
#
#    # test that it is alive again
#    assert server.worker_threads[0].is_alive()
#
#    server.manager_shutdown = True
#    server.manager_thread.join(timeout=1)
#    server.manager_shutdown = False
#
#
#def test_manager_scaling():
#    server = mock.MockHTTPServer()
#
#    server.manager_thread = threading.Thread(target=web.HTTPServer.manager, args=(server,))
#    server.manager_thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    for i in range(server.max_queue):
#        server.request_queue.put(None)
#
#    # wait a bit for thread start
#    time.sleep(server.poll_interval + 0.1)
#
#    # just make sure it is spawning some but not too many threads
#    num_threads = len(server.worker_threads)
#    assert num_threads > server.num_threads
#    assert num_threads <= server.max_threads
#
#    # mark a task as done
#    server.request_queue.get_nowait()
#    server.request_queue.task_done()
#
#    # wait a bit for another poll
#    time.sleep(server.poll_interval + 0.1)
#
#    # make sure the number didn't go down (and isn't over the max)
#    last_threads = num_threads
#    num_threads = len(server.worker_threads)
#    assert num_threads >= last_threads
#    assert num_threads <= server.max_threads
#
#    # mark all tasks as done
#    try:
#        while True:
#            server.request_queue.get_nowait()
#            server.request_queue.task_done()
#    except:
#        pass
#
#    # wait a bit for another poll
#    time.sleep(server.poll_interval + 0.1)
#
#    # make sure the number at least went down
#    last_threads = num_threads
#    num_threads = len(server.worker_threads)
#    assert num_threads < last_threads
#    assert num_threads >= server.num_threads
#
#    server.manager_shutdown = True
#    server.manager_thread.join(timeout=1)
#    server.manager_shutdown = False
#
#
#def test_worker_shutdown():
#    server = mock.MockHTTPServer()
#
#    thread = threading.Thread(target=web.HTTPServer.worker, args=(server, 0))
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    server.worker_shutdown = 0
#    thread.join(timeout=1)
#    server.worker_shutdown = None
#
#    # do it again but this time setting worker_shutdown to -1
#    thread = threading.Thread(target=web.HTTPServer.worker, args=(server, 0))
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    server.worker_shutdown = -1
#    thread.join(timeout=1)
#    server.worker_shutdown = None
#
#
#def test_worker_handle():
#    server = mock.MockHTTPServer()
#
#    thread = threading.Thread(target=web.HTTPServer.worker, args=(server, 0))
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    request = mock.MockHTTPRequest(None, None, None)
#
#    server.request_queue.put((request, False, None, True))
#
#    # wait another bit
#    time.sleep(server.poll_interval + 0.1)
#
#    assert server.request_queue.qsize() == 0
#    assert thread.is_alive()
#
#    assert request.handled == 1
#
#    server.worker_shutdown = -1
#    thread.join(timeout=1)
#    server.worker_shutdown = None
#
#
#def test_worker_handle_exception():
#    server = mock.MockHTTPServer()
#
#    thread = threading.Thread(target=web.HTTPServer.worker, args=(server, 0))
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    request = mock.MockHTTPRequest(None, None, None)
#
#    def bad_handle(self):
#        raise Exception()
#    request.handle = bad_handle
#
#    server.request_queue.put((request, False, None, True))
#
#    # wait another bit
#    time.sleep(server.poll_interval + 0.1)
#
#    assert server.request_queue.qsize() == 0
#    assert thread.is_alive()
#
#    server.worker_shutdown = -1
#    thread.join(timeout=1)
#    server.worker_shutdown = None
#
#
#def test_worker_keepalive():
#    server = mock.MockHTTPServer()
#
#    thread = threading.Thread(target=web.HTTPServer.worker, args=(server, 0))
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    request = mock.MockHTTPRequest(None, None, None, keepalive_number=2)
#
#    server.request_queue.put((request, True, None, True))
#
#    # wait for two polls
#    time.sleep(server.poll_interval + server.poll_interval + 0.1)
#
#    assert server.request_queue.qsize() == 0
#    assert thread.is_alive()
#
#    assert request.handled == 2
#    assert request.initial_timeout == server.keepalive_timeout
#
#    server.worker_shutdown = -1
#    thread.join(timeout=1)
#    server.worker_shutdown = None
#
#
#def test_worker_unhandled():
#    server = mock.MockHTTPServer()
#
#    thread = threading.Thread(target=web.HTTPServer.worker, args=(server, 0))
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    request = mock.MockHTTPRequest(None, None, None, keepalive_number=2, handle=False)
#
#    server.request_queue.put((request, True, None, True))
#
#    # wait for two polls
#    time.sleep(server.poll_interval + server.poll_interval + server.poll_interval + 0.1)
#
#    assert server.request_queue.qsize() == 0
#    assert thread.is_alive()
#
#    assert request.handled == 2
#
#    server.worker_shutdown = -1
#    thread.join(timeout=1)
#    server.worker_shutdown = None
