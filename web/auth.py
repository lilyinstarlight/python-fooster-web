import base64

import web


class AuthMixIn:
    scheme = 'None'

    def authorized(self, auth):
        return True

    def authenticate(self):
        auth_headers = web.HTTPHeaders()
        auth_headers.set('WWW-Authenticate', self.scheme)
        raise web.HTTPError(401, headers=auth_headers)

    def respond(self):
        auth = self.request.headers.get('Authorization')
        if auth is None or not self.authorized(auth):
            self.authenticate()

        return super().respond()


class AuthHandler(AuthMixIn, web.HTTPHandler):
    pass


class BasicAuthMixIn(AuthMixIn):
    scheme = 'Basic'

    def authorized(self, auth):
        user, password = base64.b64decode(auth.encode(web.default_encoding)).decode(web.default_encoding).split(':', 1)
        return self.login(user, password)


class BasicAuthHandler(BasicAuthMixIn, web.HTTPHandler):
    pass
