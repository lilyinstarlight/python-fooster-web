import json

from fooster import web


class JSONMixIn:
    def encode(self, body):
        if body is None:
            return super().encode(''.encode(web.default_encoding))

        self.response.headers.set('Content-Type', 'application/json')

        return json.dumps(body).encode(web.default_encoding)

    def decode(self, body):
        content_type = self.request.headers.get('Content-Type')
        if content_type is not None and content_type.lower().startswith('application/json'):
            return json.loads(body.decode(web.default_encoding))

        return super().decode(body)


class JSONHandler(JSONMixIn, web.HTTPHandler):
    pass


class JSONErrorMixIn:
    def respond(self):
        self.response.headers.set('Content-Type', 'application/json')

        if self.error.status_message:
            status_message = self.error.status_message
        else:
            status_message = web.status_messages[self.error.code]

        if self.error.message:
            message = self.error.message
        else:
            message = {'error': self.error.code, 'status': status_message}

        return self.error.code, status_message, json.dumps(message).encode(web.default_encoding)


class JSONErrorHandler(JSONErrorMixIn, web.HTTPErrorHandler):
    pass


def new_error(error='[0-9]{3}', handler=JSONErrorHandler):
    return {error: handler}
