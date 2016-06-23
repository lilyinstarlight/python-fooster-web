import threading
import time

from web import web


def test_acquire():
    reslock = web.ResLock()

    reslock.acquire('/', False)

    assert '/' in reslock.locks
    assert reslock.locks['/'].threads == 1

    reslock.release('/', False)

    assert '/' not in reslock.locks


def test_acquire_multiple():
    reslock = web.ResLock()

    reslock.acquire('/', False)

    def acquire_multiple():
        reslock.acquire('/', False)

    thread = threading.Thread(target=acquire_multiple)

    thread.start()

    # wait a bit
    time.sleep(0.1)

    assert thread.is_alive()
    assert reslock.locks['/'].threads == 2

    reslock.release('/', False)

    thread.join(timeout=1)

    reslock.release('/', False)

    assert '/' not in reslock.locks


def test_acquire_nonatomic():
    reslock = web.ResLock()

    reslock.acquire('/', True)

    assert '/' in reslock.locks

    reslock.release('/', True)

    assert '/' not in reslock.locks


def test_acquire_multiple_nonatomic():
    reslock = web.ResLock()

    reslock.acquire('/', True)

    def acquire_multiple_nonatomic():
        reslock.acquire('/', True)
        reslock.release('/', True)

    thread = threading.Thread(target=acquire_multiple_nonatomic)

    thread.start()

    thread.join(timeout=1)

    assert not thread.is_alive()
    assert reslock.locks['/'].threads == 1

    reslock.release('/', True)

    assert '/' not in reslock.locks


def test_acquire_multiple_read_first():
    reslock = web.ResLock()

    reslock.acquire('/', True)
    reslock.acquire('/', True)

    def acquire_multiple():
        reslock.acquire('/', False)
        reslock.release('/', False)

    thread = threading.Thread(target=acquire_multiple)

    thread.start()

    # wait a bit
    time.sleep(0.1)

    assert thread.is_alive()
    assert reslock.locks['/'].threads == 3

    reslock.release('/', True)
    reslock.release('/', True)

    thread.join(timeout=1)

    assert not thread.is_alive()

    assert '/' not in reslock.locks


def test_acquire_multiple_write_first():
    reslock = web.ResLock()

    reslock.acquire('/', False)

    def acquire_multiple():
        reslock.acquire('/', True)
        reslock.acquire('/', True)
        reslock.release('/', True)
        reslock.release('/', True)

    thread = threading.Thread(target=acquire_multiple)

    thread.start()

    # wait a bit
    time.sleep(0.1)

    assert thread.is_alive()
    assert reslock.locks['/'].threads == 2

    reslock.release('/', False)

    thread.join(timeout=1)

    assert not thread.is_alive()
    assert '/' not in reslock.locks


def test_release_no_exists():
    reslock = web.ResLock()

    try:
        reslock.release('/', False)
        assert False
    except KeyError:
        pass
