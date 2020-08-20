from fooster.web import web


import pytest


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
case_header_test = case_key + ': ' + test_value + '\r\n'

nonstr_key = 6
nonstr_value = None


def test_add_get():
    headers = web.HTTPHeaders()

    headers.add(test_header)

    assert headers.get(test_key) == test_value


def test_add_getlist():
    headers = web.HTTPHeaders()

    headers.add(test_header)

    assert headers.getlist(test_key) == [test_value]


def test_add_getitem():
    headers = web.HTTPHeaders()

    headers.add(test_header)

    assert headers[test_key] == test_value


def test_getitem_empty():
    headers = web.HTTPHeaders()

    with pytest.raises(KeyError):
        headers[test_key]


def test_getlist_empty():
    headers = web.HTTPHeaders()

    with pytest.raises(KeyError):
        headers.getlist(test_key)


def test_getlist_default():
    headers = web.HTTPHeaders()

    assert headers.getlist(test_key, []) == []


def test_set_remove():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)

    assert headers.get(test_key) == test_value

    headers.remove(test_key)


def test_set_multiple():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)
    headers.set(test_key, test_value)

    assert headers.get(test_key) == test_value
    assert headers.getlist(test_key) == [test_value] * 2


def test_set_overwrite():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value, True)
    headers.set(test_key, test_value, True)

    assert headers.get(test_key) == test_value
    assert headers.getlist(test_key) == [test_value]


def test_setitem_delitem():
    headers = web.HTTPHeaders()

    headers[test_key] = test_value

    assert headers[test_key] == test_value

    del headers[test_key]


def test_remove_empty():
    headers = web.HTTPHeaders()

    with pytest.raises(KeyError):
        headers.remove(test_key)


def test_delitem_empty():
    headers = web.HTTPHeaders()

    with pytest.raises(KeyError):
        del headers[test_key]


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


def test_multiple_add_get_len_retrieve():
    headers = web.HTTPHeaders()

    headers.add(case_header)

    assert len(headers) == 1
    assert headers.get(case_key) == case_value
    assert headers.getlist(case_key) == [case_value]
    assert headers.retrieve(case_key) == case_header

    headers.add(case_header)

    assert len(headers) == 1
    assert headers.get(case_key) == case_value
    assert headers.getlist(case_key) == [case_value] * 2
    assert headers.retrieve(case_key) == case_header + case_header

    headers.add(case_header_test)

    assert len(headers) == 1
    assert headers.get(case_key) == test_value
    assert headers.getlist(case_key) == [case_value] * 2 + [test_value]
    assert headers.retrieve(case_key) == case_header + case_header + case_header_test


def test_multiple_set_get_len_retrieve():
    headers = web.HTTPHeaders()

    headers.set(case_key, case_value)

    assert len(headers) == 1
    assert headers.get(case_key) == case_value
    assert headers.getlist(case_key) == [case_value]
    assert headers.retrieve(case_key) == case_header

    headers.set(case_key, case_value)

    assert len(headers) == 1
    assert headers.get(case_key) == case_value
    assert headers.getlist(case_key) == [case_value] * 2
    assert headers.retrieve(case_key) == case_header + case_header

    headers.set(case_key, test_value)

    assert len(headers) == 1
    assert headers.get(case_key) == test_value
    assert headers.getlist(case_key) == [case_value] * 2 + [test_value]
    assert headers.retrieve(case_key) == case_header + case_header + case_header_test


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


def test_contains():
    headers = web.HTTPHeaders()

    headers.set(test_key, test_value)
    headers.set(poor_key, poor_value)
    headers.set(case_key, case_value)

    assert test_key in headers
    assert poor_key in headers
    assert case_key in headers

    assert test_key.upper() in headers
    assert poor_key.upper() in headers
    assert case_key.upper() in headers

    assert test_key.lower() in headers
    assert poor_key.lower() in headers
    assert case_key.lower() in headers


def test_poor_header():
    headers = web.HTTPHeaders()

    headers.add(poor_header)

    assert headers.get(poor_key) == poor_value


def test_set_key_nonstr():
    headers = web.HTTPHeaders()

    with pytest.raises(TypeError):
        headers.set(nonstr_key, test_value)


def test_set_value_nonstr():
    headers = web.HTTPHeaders()

    with pytest.raises(TypeError):
        headers.set(test_key, nonstr_value)
