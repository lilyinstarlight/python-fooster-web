import threading
import time

from web import web

def test_acquire():
	reslock = web.ResLock()

	reslock.acquire('/')

	assert '/' in reslock.locks
	assert '/' in reslock.locks_count
	assert reslock.locks_count['/'] == 1

	reslock.release('/')

	assert '/' not in reslock.locks
	assert '/' not in reslock.locks_count

def test_acquire_exists():
	reslock = web.ResLock()

	reslock.acquire('/')

	def acquire_exists():
		reslock.acquire('/')

	thread = threading.Thread(target=acquire_exists)

	thread.start()

	#Wait a bit
	time.sleep(0.1)

	assert thread.is_alive()
	assert reslock.locks_count['/'] == 2

	reslock.release('/')

	thread.join(timeout=1)

	reslock.release('/')

	assert '/' not in reslock.locks
	assert '/' not in reslock.locks_count

def test_release_no_exists():
	reslock = web.ResLock()

	try:
		reslock.release('/')
		assert False
	except KeyError:
		pass

def test_wait():
	reslock = web.ResLock()

	reslock.wait('/')

	assert '/' not in reslock.locks
	assert '/' not in reslock.locks_count

def test_wait_exists():
	reslock = web.ResLock()

	reslock.acquire('/')

	def wait_exists():
		reslock.wait('/')

	thread = threading.Thread(target=wait_exists)

	thread.start()

	#Wait a bit
	time.sleep(0.1)

	assert thread.is_alive()
	assert reslock.locks_count['/'] == 1

	reslock.release('/')

	thread.join(timeout=1)

	assert '/' not in reslock.locks
	assert '/' not in reslock.locks_count
