import web


class AuthMixIn:
    pass


class AuthHandler(AuthMixIn, web.HTTPHandler):
    pass
