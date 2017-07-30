#import threading
#import time
#
#from web import web
#
#
#def test_acquire():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', False)
#
#    assert '/' in reslock.locks
#    assert reslock.locks['/'][0].threads == 1
#
#    reslock.release('/', False)
#
#    assert '/' not in reslock.locks
#
#
#def test_acquire_multiple():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', False)
#
#    def acquire_multiple():
#        while not reslock.acquire(object(), '/', False):
#            time.sleep(0.1)
#
#    thread = threading.Thread(target=acquire_multiple)
#
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    assert thread.is_alive()
#    assert reslock.locks['/'][0].threads == 1
#
#    reslock.release('/', False)
#
#    thread.join(timeout=1)
#
#    reslock.release('/', False)
#
#    assert '/' not in reslock.locks
#
#
#def test_acquire_nonatomic():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', True)
#
#    assert '/' in reslock.locks
#
#    reslock.release('/', True)
#
#    assert '/' not in reslock.locks
#
#
#def test_acquire_multiple_nonatomic():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', True)
#
#    def acquire_multiple_nonatomic():
#        reslock.acquire(object(), '/', True)
#        reslock.release('/', True)
#
#    thread = threading.Thread(target=acquire_multiple_nonatomic)
#
#    thread.start()
#
#    thread.join(timeout=1)
#
#    assert not thread.is_alive()
#    assert reslock.locks['/'][0].threads == 1
#
#    reslock.release('/', True)
#
#    assert '/' not in reslock.locks
#
#
#def test_acquire_multiple_read_first():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', True)
#    assert reslock.acquire(object(), '/', True)
#
#    def acquire_multiple():
#        while not reslock.acquire(object(), '/', False):
#            time.sleep(0.1)
#        reslock.release('/', False)
#
#    thread = threading.Thread(target=acquire_multiple)
#
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    assert thread.is_alive()
#    assert reslock.locks['/'][0].threads == 3
#
#    reslock.release('/', True)
#    reslock.release('/', True)
#
#    thread.join(timeout=1)
#
#    assert not thread.is_alive()
#
#    assert '/' not in reslock.locks
#
#
#def test_acquire_multiple_write_first():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', False)
#
#    def acquire_multiple():
#        while not reslock.acquire(object(), '/', True):
#            time.sleep(0.1)
#        while not reslock.acquire(object(), '/', True):
#            time.sleep(0.1)
#        reslock.release('/', True)
#        reslock.release('/', True)
#
#    thread = threading.Thread(target=acquire_multiple)
#
#    thread.start()
#
#    # wait a bit
#    time.sleep(0.1)
#
#    assert thread.is_alive()
#    assert reslock.locks['/'][0].threads == 1
#
#    reslock.release('/', False)
#
#    thread.join(timeout=1)
#
#    assert not thread.is_alive()
#    assert '/' not in reslock.locks
#
#
#def test_acquire_not_last():
#    reslock = web.ResLock()
#
#    assert reslock.acquire(object(), '/', True)
#    assert reslock.acquire(object(), '/', True)
#
#    assert reslock.locks['/'][0].threads == 2
#
#    reslock.release('/', True, False)
#
#    assert reslock.locks['/'][0].threads == 1
#
#    reslock.release('/', True, False)
#
#    assert reslock.locks['/'][0].threads == 1
#
#    reslock.release('/', True)
#
#    assert '/' not in reslock.locks
#
#
#def test_acquire_reentrant():
#    reslock = web.ResLock()
#
#    request = 'token'
#
#    assert reslock.acquire(request, '/', False)
#    assert reslock.acquire(request, '/', False)
#
#    assert not reslock.acquire(object(), '/', False)
#
#    assert reslock.locks['/'][0].threads == 2
#
#    reslock.release('/', False)
#    reslock.release('/', False)
#
#    assert '/' not in reslock.locks
#
#
#def test_release_no_exists():
#    reslock = web.ResLock()
#
#    try:
#        reslock.release('/', False)
#        assert False
#    except KeyError:
#        pass
