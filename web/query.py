import re
import urllib.parse


regex = '(?:\?([\w=&%.+]*))?'


class QueryMixIn:
    group = 0

    def respond(self):
        self.request.query = dict(urllib.parse.parse_qsl(self.groups[self.group], True))

        return super().respond()


def new(base, handler):
    class GenQueryHandler(QueryMixIn, handler):
        pass

    GenQueryHandler.group = re.compile(base).groups

    return {base + regex: GenQueryHandler}
