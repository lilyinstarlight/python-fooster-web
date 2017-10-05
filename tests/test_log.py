import logging
import time

from fooster.web import web


test_record = ('test', logging.DEBUG, 'test_log.py', 5, ('127.0.0.1', 'GET / HTTP/1.1', 204, 0, '-', '-'), (), None)


def test_filter():
    record = logging.LogRecord(*test_record)

    assert web.HTTPLogFilter().filter(record)

    assert record.host == '127.0.0.1' and record.request == 'GET / HTTP/1.1' and record.code == 204 and record.size == 0 and record.ident == '-' and record.authuser == '-'


def test_format():
    record = logging.LogRecord(*test_record)
    assert web.HTTPLogFilter().filter(record)

    formatted = web.HTTPLogFormatter().format(record)

    assert formatted == '127.0.0.1 - - [{}] "GET / HTTP/1.1" 204 0'.format(time.strftime('%d/%b/%Y:%H:%M:%S %z', time.localtime(record.created)))
