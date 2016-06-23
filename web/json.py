import web


class JSONMixIn:
    pass


class JSONHandler(JSONMixIn, web.HTTPHandler):
    pass
