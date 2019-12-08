import urllib.parse

from fooster import web


regex = r'(?:\?(?P<query>[\w=&%.+]*))?'


class QueryMixIn:
    querystr = None

    def respond(self):
        if self.querystr is None and 'query' in self.groups:
            self.querystr = self.groups['query']

        if self.querystr is not None:
            self.request.query = dict(urllib.parse.parse_qsl(self.querystr, True))
        else:
            self.request.query = None

        return super().respond()


class QueryHandler(QueryMixIn, web.HTTPHandler):
    pass


def new(base, handler):
    return {base + regex: handler}
