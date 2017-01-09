import re
import urllib.parse

import web


regex = '\?([\w=&])'


class QueryMixIn:
    group = 0

    def respond(self):
        self.request.params = dict(urllib.parse.parse_qsl(self.groups[self.group], True))


def new(base, handler):
    class GenQueryHandler(handler, QueryMixIn):
        pass

    GenQueryHandler.group = re.compile(base).groups + 1

    return {base + regex: handler}
