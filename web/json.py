import json

import web


class JSONMixIn:
    def encode(self, body):
        self.response.headers.set('Content-Type', 'application/json')

        return json.dumps(body)

    def decode(self, body):
        if self.request.headers.get('Content-Type').lower() == 'application/json':
            return json.loads(self.request.body)

        return super().decode(body)


class JSONHandler(JSONMixIn, web.HTTPHandler):
    pass
