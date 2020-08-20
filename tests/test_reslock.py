import multiprocessing
import os
import time

from fooster.web import web


import pytest


def acquire_multiple(reslock):
    while not reslock.acquire('second', '/', False):
        time.sleep(1)


def acquire_multiple_nonatomic(reslock):
    reslock.acquire('second', '/', True)
    reslock.release('/', True)


def acquire_multiple_read_first(reslock):
    while not reslock.acquire('third', '/', False):
        time.sleep(1)
    reslock.release('/', False)


def acquire_multiple_write_first(reslock):
    while not reslock.acquire('second', '/', True):
        time.sleep(1)
    while not reslock.acquire('third', '/', True):
        time.sleep(1)
    reslock.release('/', True)
    reslock.release('/', True)


def test_acquire():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', False)

    assert os.listdir(reslock.directory)
    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 1

    reslock.release('/', False)

    assert not os.listdir(reslock.directory)


def test_acquire_multiple():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', False)

    process = multiprocessing.get_context('spawn').Process(target=acquire_multiple, args=(reslock,))

    process.start()

    # wait a bit
    time.sleep(1)

    assert process.is_alive()
    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 1

    reslock.release('/', False)

    process.join(timeout=1)

    reslock.release('/', False)

    assert not os.listdir(reslock.directory)


def test_acquire_nonatomic():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', True)

    assert os.listdir(reslock.directory)

    reslock.release('/', True)

    assert not os.listdir(reslock.directory)


def test_acquire_multiple_nonatomic():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', True)

    process = multiprocessing.get_context('spawn').Process(target=acquire_multiple_nonatomic, args=(reslock,))

    process.start()

    process.join(timeout=1)

    assert not process.is_alive()
    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 1

    reslock.release('/', True)

    assert not os.listdir(reslock.directory)


def test_acquire_multiple_read_first():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', True)
    assert reslock.acquire('second', '/', True)

    process = multiprocessing.get_context('spawn').Process(target=acquire_multiple_read_first, args=(reslock,))

    process.start()

    # wait a bit
    time.sleep(1)

    assert process.is_alive()
    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 3

    reslock.release('/', True)
    reslock.release('/', True)

    process.join(timeout=1)

    assert not process.is_alive()

    assert not os.listdir(reslock.directory)


def test_acquire_multiple_write_first():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', False)

    process = multiprocessing.get_context('spawn').Process(target=acquire_multiple_write_first, args=(reslock,))

    process.start()

    # wait a bit
    time.sleep(1)

    assert process.is_alive()
    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 1

    reslock.release('/', False)

    process.join(timeout=1)

    assert not process.is_alive()
    assert not os.listdir(reslock.directory)


def test_acquire_not_last():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/', True)
    assert reslock.acquire('second', '/', True)

    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 2

    reslock.release('/', True, False)

    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 1

    reslock.release('/', True, False)

    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 1

    reslock.release('/', True)

    assert not os.listdir(reslock.directory)


def test_acquire_reentrant():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    request = 'token'

    assert reslock.acquire(request, '/', False)
    assert reslock.acquire(request, '/', False)

    assert not reslock.acquire('first', '/', False)

    assert web.ResLock.LockProxy(reslock.directory, '/').processes == 2

    reslock.release('/', False)
    reslock.release('/', False)

    assert not os.listdir(reslock.directory)


def test_acquire_request_multiple():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    assert reslock.acquire('first', '/first', True)
    assert reslock.acquire('first', '/second', True)

    assert web.ResLock.LockProxy(reslock.directory, '/first').processes == 1
    assert web.ResLock.LockProxy(reslock.directory, '/second').processes == 1

    reslock.release('/first', True)
    reslock.release('/second', True)

    assert not os.listdir(reslock.directory)


def test_release_no_exists():
    sync = multiprocessing.get_context('spawn').Manager()

    reslock = web.ResLock(sync)

    with pytest.raises(RuntimeError):
        reslock.release('/', False)
