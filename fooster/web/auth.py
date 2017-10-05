import base64

from fooster import web


class AuthError(web.HTTPError):
    def __init__(self, scheme, realm, code=401, message=None, headers=None, status_message=None):
        super().__init__(code, message, headers, status_message)

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

    def forbidden(self):
        return False

    def authorized(self, token):
        scheme = self.scheme.lower()

        if not hasattr(self, 'auth_' + scheme):
            raise AuthError(','.join(scheme.title() for scheme in self.schemes()), self.realm)

        return getattr(self, 'auth_' + scheme)(token)

    def respond(self):
        auth = self.request.headers.get('Authorization')

        try:
            self.scheme, token = auth.split(' ', 1)
        except Exception:
            raise AuthError(','.join(scheme.title() for scheme in self.schemes()), self.realm)

        self.auth = self.authorized(token)

        if self.forbidden():
            raise web.HTTPError(403)

        return super().respond()


class AuthHandler(AuthMixIn, web.HTTPHandler):
    pass


class BasicAuthMixIn(AuthMixIn):
    def auth_basic(self, token):
        user, password = base64.b64decode(token.encode(web.default_encoding)).decode(web.default_encoding).split(':', 1)

        auth = self.login(user, password)

        if not auth:
            raise AuthError('Basic', self.realm)

        return auth


class BasicAuthHandler(BasicAuthMixIn, web.HTTPHandler):
    pass


class TokenAuthMixIn(AuthMixIn):
    def auth_token(self, token):
        auth = self.token(token)

        if not auth:
            raise AuthError('Token', self.realm)

        return auth


class TokenAuthHandler(TokenAuthMixIn, web.HTTPHandler):
    pass
