from fooster.web import web


test_key = 'Magical'
test_value = 'header'
test_header = test_key + ': ' + test_value + '\r\n'

poor_key = 'not'
poor_value = 'good'
poor_header = poor_key + ':' + poor_value + '\r\n'
good_header = poor_key + ': ' + poor_value + '\r\n'

case_key = 'wEIrd'
case_key_title = case_key.title()
case_value = 'cAse'
case_header = case_key + ': ' + case_value + '\r\n'

nonstr_key = 6
nonstr_value = None


def test_add_get():
    headers = web.HTTPHeaders()

    headers.add(test_header)

    assert headers.get(test_key) == test_value


def test_add_getitem():
    headers = web.HTTPHeaders()

    headers.add(test_header)

    assert headers[test_key] == test_value


def test_getitem_empty():
    headers = web.HTTPHeaders()

    try:
        headers[test_key]
        assert False
    except KeyError:
        pass


def test_set_remove():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)

    assert headers.get(test_key) == test_value

    headers.remove(test_key)


def test_setitem_delitem():
    headers = web.HTTPHeaders()

    headers[test_key] = test_value

    assert headers[test_key] == test_value

    del headers[test_key]


def test_remove_empty():
    headers = web.HTTPHeaders()

    try:
        headers.remove(test_key)
        assert False
    except KeyError:
        pass


def test_delitem_empty():
    headers = web.HTTPHeaders()

    try:
        del headers[test_key]
        assert False
    except KeyError:
        pass


def test_retrieve():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)

    assert headers.retrieve(test_key) == test_header


def test_len():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)

    assert len(headers) == 1

    headers.set(poor_key, poor_value)

    assert len(headers) == 2


def test_clear():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)
    headers.set(poor_key, poor_value)

    headers.clear()

    assert len(headers) == 0


def test_case():
    headers = web.HTTPHeaders()

    headers.set(case_key, case_value)

    assert headers.get(case_key_title) == case_value

    assert headers.retrieve(case_key_title) == case_header


def test_iter():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)
    headers.set(poor_key, poor_value)
    headers.set(case_key, case_value)

    header_list = []

    for header in headers:
        header_list.append(header)

    assert test_header in header_list
    assert good_header in header_list
    assert case_header in header_list


def test_poor_header():
    headers = web.HTTPHeaders()

    headers.add(poor_header)

    assert headers.get(poor_key) == poor_value


def test_set_key_nonstr():
    headers = web.HTTPHeaders()

    try:
        headers.set(nonstr_key, test_value)
        assert False
    except TypeError:
        pass


def test_set_value_nonstr():
    headers = web.HTTPHeaders()

    try:
        headers.set(test_key, nonstr_value)
        assert False
    except TypeError:
        pass
