import multiprocessing
import os
import time

from fooster.web import web


import pytest


def acquire_release_reader(res_lock):
    res_lock.acquire('second', '/', False)
    res_lock.release('/', False)


def acquire_wait_writer(res_lock):
    while not res_lock.acquire('second', '/', True):
        time.sleep(1)


def acquire_wait_release_writer(res_lock):
    while not res_lock.acquire('third', '/', True):
        time.sleep(1)
    res_lock.release('/', True)


def acquire_wait_release_multiple_readers(res_lock):
    while not res_lock.acquire('second', '/', False):
        time.sleep(1)
    while not res_lock.acquire('third', '/', False):
        time.sleep(1)
    res_lock.release('/', False)
    res_lock.release('/', False)


def test_acquire():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    assert res_lock.acquire('first', '/', False)

    assert res_lock.resources
    assert res_lock.resources['/'][1] == 1

    res_lock.release('/', False)

    assert not res_lock.resources


def test_acquire_multiple():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    print(res_lock.resources)
    assert res_lock.acquire('first', '/', False)
    print(res_lock.resources)

    process = multiprocessing.get_context(web.start_method).Process(target=acquire_release_reader, args=(res_lock,))

    process.start()

    process.join(timeout=1)

    assert not process.is_alive()
    assert res_lock.resources['/'][1] == 1

    res_lock.release('/', False)

    assert not res_lock.resources


def test_acquire_write():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    assert res_lock.acquire('first', '/', True)

    assert res_lock.resources

    res_lock.release('/', True)

    assert not res_lock.resources


def test_acquire_multiple_write():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    print(res_lock.resources)
    assert res_lock.acquire('first', '/', True)
    print(res_lock.resources)

    process = multiprocessing.get_context(web.start_method).Process(target=acquire_wait_writer, args=(res_lock,))

    process.start()

    # wait a bit
    time.sleep(1)

    assert process.is_alive()
    assert res_lock.resources['/'][1] == 1

    res_lock.release('/', True)

    process.join(timeout=1)

    res_lock.release('/', True)

    assert not res_lock.resources


def test_acquire_multiple_read_first():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    assert res_lock.acquire('first', '/', False)
    assert res_lock.acquire('second', '/', False)

    process = multiprocessing.get_context(web.start_method).Process(target=acquire_wait_release_writer, args=(res_lock,))

    process.start()

    # wait a bit
    time.sleep(1)

    assert process.is_alive()
    assert res_lock.resources['/'][1] == 3

    res_lock.release('/', False)
    res_lock.release('/', False)

    process.join(timeout=1)

    assert not process.is_alive()
    assert not res_lock.resources


def test_acquire_multiple_write_first():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    assert res_lock.acquire('first', '/', True)

    process = multiprocessing.get_context(web.start_method).Process(target=acquire_wait_release_multiple_readers, args=(res_lock,))

    process.start()

    # wait a bit
    time.sleep(1)

    assert process.is_alive()
    assert res_lock.resources['/'][1] == 1

    res_lock.release('/', True)

    process.join(timeout=1)

    assert not process.is_alive()
    assert not res_lock.resources


def test_acquire_reentrant():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    request = 'token'

    assert res_lock.acquire(request, '/', True)
    assert res_lock.acquire(request, '/', True)

    assert not res_lock.acquire('first', '/', True)

    assert res_lock.resources['/'][1] == 2

    res_lock.release('/', True)
    res_lock.release('/', True)

    assert not res_lock.resources


def test_acquire_request_multiple():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    assert res_lock.acquire('first', '/first', True)
    assert res_lock.acquire('first', '/second', True)

    assert res_lock.resources['/first'][1] == 1
    assert res_lock.resources['/second'][1] == 1

    res_lock.release('/first', True)
    res_lock.release('/second', True)

    assert not res_lock.resources


def test_release_no_exists():
    sync = multiprocessing.get_context(web.start_method).Manager()

    res_lock = web.ResLock(sync)

    with pytest.raises(RuntimeError):
        res_lock.release('/', False)
