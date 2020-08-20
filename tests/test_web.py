import logging
import time

from fooster.web import web


def test_mktime():
    assert web.mktime(time.gmtime(0)) == 'Thu, 01 Jan 1970 00:00:00 GMT'


def test_mklog_web():
    log = web.mklog('web')

    assert log is logging.getLogger('web')


def test_mklog_http():
    http_log = web.mklog('http', access_log=True)

    assert http_log is logging.getLogger('http')
    assert any(any(isinstance(filter, web.HTTPLogFilter) for filter in handler.filters) and isinstance(handler.formatter, web.HTTPLogFormatter) for handler in http_log.handlers)
