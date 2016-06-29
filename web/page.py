import web


class PageHandler(web.HTTPHandler):
    directory = '.'
    page = 'index.html'

    def format(self, page):
        return page

    def do_get(self):
        self.response.headers.set('Content-Type', 'text/html')

        with open(self.directory + '/' + self.page, 'r') as file:
            page = file.read()

        return 200, self.format(page)
