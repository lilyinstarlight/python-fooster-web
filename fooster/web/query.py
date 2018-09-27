import re
import urllib.parse

from fooster import web


regex = r'(?:\?(?P<query>[\w=&%.+]*))?'


class QueryMixIn:
    def respond(self):
        if 'query' in self.groups:
            self.request.query = dict(urllib.parse.parse_qsl(self.groups['query'], True))
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
