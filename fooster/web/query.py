import collections
import urllib.parse

from fooster import web


__all__ = ['regex', 'QueryMixIn', 'QueryHandler', 'new']


regex = r'(?:\?(?P<query>[\w&= !"#$%\'()*+,./:;<>?@[\\\]^`{|}~-]*))?'


class QueryMixIn:
    querystr = None

    def respond(self):
        if self.querystr is None and 'query' in self.groups:
            self.querystr = self.groups['query']

        if self.querystr is not None:
            try:
                self.request.query = collections.OrderedDict(urllib.parse.parse_qsl(self.querystr, True))
            except Exception as error:
                raise web.HTTPError(400) from error
        else:
            self.request.query = None

        return super().respond()


class QueryHandler(QueryMixIn, web.HTTPHandler):
    pass


def new(base, handler):
    return {base + regex: handler}
