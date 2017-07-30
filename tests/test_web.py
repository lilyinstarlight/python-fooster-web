import time

from web import web


def test_mktime():
    web_time = web.mktime(time.gmtime(0))

    assert web_time == 'Thu, 01 Jan 1970 00:00:00 GMT' or web_time == 'Thu, 01 Jan 1970 00:00:00 UTC'
