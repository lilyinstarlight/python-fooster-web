import json

import web


class JSONMixIn:
    def encode(self, body):
        self.response.headers.set('Content-Type', 'application/json')

        return json.dumps(body).encode(web.default_encoding)

    def decode(self, body):
        content_type = self.request.headers.get('Content-Type')
        if content_type is not None and content_type.lower() == 'application/json':
            return json.loads(body.decode(web.default_encoding))

        return super().decode(body)


class JSONHandler(JSONMixIn, web.HTTPHandler):
    pass
