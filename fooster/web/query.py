import re
import urllib.parse

from fooster import web


regex = '(?:\?([\w=&%.+]*))?'


class QueryMixIn:
    group = 0

    def respond(self):
        if len(self.groups) > self.group and self.groups[self.group]:
            self.request.query = dict(urllib.parse.parse_qsl(self.groups[self.group], True))
        else:
            self.request.query = None

        return super().respond()


class QueryHandler(QueryMixIn, web.HTTPHandler):
    pass


def new(base, handler):
    class GenQueryHandler(QueryMixIn, handler):
        pass

    GenQueryHandler.group = re.compile(base).groups

    return {base + regex: GenQueryHandler}
