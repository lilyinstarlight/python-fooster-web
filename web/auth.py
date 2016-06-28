import base64

import web


class AuthError(web.HTTPError):
    def __init__(self, scheme, realm, code=401, message=None, headers=None, status_message=None):
        super.__init__(code, message, headers, status_message)

        self.scheme = scheme
        self.realm = realm

        if self.headers is None:
            self.headers = web.HTTPHeaders()

        self.headers.set('WWW-Authenticate', self.scheme + ' realm="' + self.realm + '"')


class AuthMixIn:
    realm = 'Unknown'

    def schemes(self):
        # lots of magic for finding all lower case attributes beginning with 'auth_' and removing the 'auth_'
        return (scheme[5:] for scheme in dir(self) if scheme.startswith('auth_') and scheme.islower())

    def authorized(self, scheme, token):
        if not hasattr(self, 'auth_' + self.method):
            raise AuthError(','.join(scheme.title() for scheme in self.schemes()), self.realm)

        return getattr(self, 'auth_' + self.method)()

    def respond(self):
        auth = self.request.headers.get('Authorization')

        if not auth:
            raise AuthError(self.default, self.realm)

        scheme, token = auth.split(' ', 1)

        self.auth = self.authorized(scheme, token)

        return super().respond()


class AuthHandler(AuthMixIn, web.HTTPHandler):
    pass


class BasicAuthMixIn(AuthMixIn):
    def auth_basic(self, auth):
        user, password = base64.b64decode(auth.encode(web.default_encoding)).decode(web.default_encoding).split(':', 1)

        auth = self.login(user, password)

        if not auth:
            raise AuthError('Basic', self.realm)

        return auth


class BasicAuthHandler(BasicAuthMixIn, web.HTTPHandler):
    pass


class TokenAuthMixIn(AuthMixIn):
    def auth_token(self, auth):
        auth = self.token(auth)

        if not auth:
            raise AuthError('Token', self.realm)

        return auth


class TokenAuthHandler(TokenAuthMixIn, web.HTTPHandler):
    pass
