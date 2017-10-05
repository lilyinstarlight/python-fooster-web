import time

from fooster.web import web


def test_mktime():
    assert web.mktime(time.gmtime(0)) == 'Thu, 01 Jan 1970 00:00:00 GMT'
