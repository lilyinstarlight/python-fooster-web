#import os
#
#from web import web
#
#import pytest
#
#
#message = 'This is just a test'
#
#
#def make_log(tmp):
#    if tmp:
#        httpd_log = os.path.join(tmp, 'httpd.log')
#        access_log = os.path.join(tmp, 'access.log')
#    else:
#        httpd_log = None
#        access_log = None
#
#    return web.HTTPLog(httpd_log, access_log)
#
#
#def test_log_none():
#    log = make_log(None)
#
#    assert hasattr(log, 'httpd_log')
#    assert hasattr(log.httpd_log, 'write')
#
#    assert hasattr(log, 'access_log')
#    assert hasattr(log.access_log, 'write')
#
#
#@pytest.fixture(scope='function')
#def tmp(tmpdir):
#    return str(tmpdir)
#
#
#def test_mkdir(tmp):
#    make_log(tmp)
#
#    assert os.path.exists(tmp)
#    assert os.path.exists(os.path.join(tmp, 'httpd.log'))
#    assert os.path.exists(os.path.join(tmp, 'access.log'))
#
#
#def test_message(tmp):
#    log = make_log(tmp)
#
#    log.message(message)
#    with open(log.httpd_log.name) as log_file:
#        value = log_file.read()
#
#    assert value.endswith(message + '\n')
#
#
#def test_info(tmp):
#    log = make_log(tmp)
#
#    log.info(message)
#    with open(log.httpd_log.name) as log_file:
#        value = log_file.read()
#
#    assert value.endswith('INFO: ' + message + '\n')
#
#
#def test_warning(tmp):
#    log = make_log(tmp)
#
#    log.warning(message)
#    with open(log.httpd_log.name) as log_file:
#        value = log_file.read()
#
#    assert value.endswith('WARNING: ' + message + '\n')
#
#
#def test_error(tmp):
#    log = make_log(tmp)
#
#    log.error(message)
#    with open(log.httpd_log.name) as log_file:
#        value = log_file.read()
#
#    assert value.endswith('ERROR: ' + message + '\n')
#
#
#def test_exception(tmp):
#    log = make_log(tmp)
#
#    try:
#        raise Exception()
#    except:
#        log.exception()
#    with open(log.httpd_log.name) as log_file:
#        value = log_file.readline()
#
#    assert value.endswith('ERROR: Caught exception:\n')
#
#
#def test_request(tmp):
#    log = make_log(tmp)
#
#    log.request('localhost', 'GET / HTTP/1.1', '200', '1024', '-', '-')
#    with open(log.access_log.name) as log_file:
#        value = log_file.read()
#
#    # test for standard HTTP log format
#
#    assert value.startswith('localhost - - [')
#    # timestamp here
#    assert value.endswith('] "GET / HTTP/1.1" 200 1024\n')
