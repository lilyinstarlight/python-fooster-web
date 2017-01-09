import re
import urllib.parse

import web


class QueryMixIn:
    group = 0

    def respond(self):
        self.request.params = dict(urllib.parse.parse_qsl(self.groups[self.group], True))


class QueryHandler(QueryMixIn, web.HTTPHandler):
    pass


def new(base, handler=QueryHandler):
    class GenQueryHandler(handler):
        pass

    GenQueryHandler.group = re.compile(base).groups + 1

    return {base + '\?([\w=&])': handler}
