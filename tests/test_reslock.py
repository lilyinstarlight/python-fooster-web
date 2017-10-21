import multiprocessing
import os
import time

from fooster.web import web

import util


def test_acquire():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', False)

    assert os.listdir(reslock.dir)
    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 1

    reslock.release('/', False)

    assert not os.listdir(reslock.dir)


def test_acquire_multiple():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', False)

    def acquire_multiple():
        while not reslock.acquire('second', '/', False):
            time.sleep(0.1)

    process = multiprocessing.Process(target=acquire_multiple)

    process.start()

    # wait a bit
    time.sleep(0.1)

    assert process.is_alive()
    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 1

    reslock.release('/', False)

    process.join(timeout=1)

    reslock.release('/', False)

    assert not os.listdir(reslock.dir)


def test_acquire_nonatomic():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', True)

    assert os.listdir(reslock.dir)

    reslock.release('/', True)

    assert not os.listdir(reslock.dir)


def test_acquire_multiple_nonatomic():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', True)

    def acquire_multiple_nonatomic():
        reslock.acquire('second', '/', True)
        reslock.release('/', True)

    process = multiprocessing.Process(target=acquire_multiple_nonatomic)

    process.start()

    process.join(timeout=1)

    assert not process.is_alive()
    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 1

    reslock.release('/', True)

    assert not os.listdir(reslock.dir)


def test_acquire_multiple_read_first():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', True)
    assert reslock.acquire('second', '/', True)

    def acquire_multiple():
        while not reslock.acquire('third', '/', False):
            time.sleep(0.1)
        reslock.release('/', False)

    process = multiprocessing.Process(target=acquire_multiple)

    process.start()

    # wait a bit
    time.sleep(0.1)

    assert process.is_alive()
    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 3

    reslock.release('/', True)
    reslock.release('/', True)

    process.join(timeout=1)

    assert not process.is_alive()

    assert not os.listdir(reslock.dir)


def test_acquire_multiple_write_first():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', False)

    def acquire_multiple():
        while not reslock.acquire('second', '/', True):
            time.sleep(0.1)
        while not reslock.acquire('third', '/', True):
            time.sleep(0.1)
        reslock.release('/', True)
        reslock.release('/', True)

    process = multiprocessing.Process(target=acquire_multiple)

    process.start()

    # wait a bit
    time.sleep(0.1)

    assert process.is_alive()
    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 1

    reslock.release('/', False)

    process.join(timeout=1)

    assert not process.is_alive()
    assert not os.listdir(reslock.dir)


def test_acquire_not_last():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/', True)
    assert reslock.acquire('second', '/', True)

    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 2

    reslock.release('/', True, False)

    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 1

    reslock.release('/', True, False)

    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 1

    reslock.release('/', True)

    assert not os.listdir(reslock.dir)


def test_acquire_reentrant():
    reslock = web.ResLock(util.sync)

    request = 'token'

    assert reslock.acquire(request, '/', False)
    assert reslock.acquire(request, '/', False)

    assert not reslock.acquire('first', '/', False)

    assert web.ResLock.LockProxy(reslock.dir, '/').processes == 2

    reslock.release('/', False)
    reslock.release('/', False)

    assert not os.listdir(reslock.dir)


def test_acquire_request_multiple():
    reslock = web.ResLock(util.sync)

    assert reslock.acquire('first', '/first', True)
    assert reslock.acquire('first', '/second', True)

    assert web.ResLock.LockProxy(reslock.dir, '/first').processes == 1
    assert web.ResLock.LockProxy(reslock.dir, '/second').processes == 1

    reslock.release('/first', True)
    reslock.release('/second', True)

    assert not os.listdir(reslock.dir)


def test_release_no_exists():
    reslock = web.ResLock(util.sync)

    try:
        reslock.release('/', False)
        assert False
    except RuntimeError:
        pass
