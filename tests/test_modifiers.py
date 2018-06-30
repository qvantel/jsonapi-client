from jsonapi_client.filter import Inclusion, Modifier


def test_modifier():
    url = 'http://localhost:8080'
    query = 'example_attr=1'
    m = Modifier(query)
    assert m.url_with_modifiers(url) == f'{url}?{query}'


def test_inclusion():
    url = 'http://localhost:8080'
    f = Inclusion('something', 'something_else')
    assert f.url_with_modifiers(url) == f'{url}?include=something,something_else'


def test_modifier_sum():
    url = 'http://localhost:8080'
    q1 = 'item1=1'
    q2 = 'item2=2'
    q3 = 'item3=3'
    m1 = Modifier(q1)
    m2 = Modifier(q2)
    m3 = Modifier(q3)

    assert ((m1 + m2) + m3).url_with_modifiers(url) == f'{url}?{q1}&{q2}&{q3}'
    assert (m1 + (m2 + m3)).url_with_modifiers(url) == f'{url}?{q1}&{q2}&{q3}'
    assert (m1 + m2 + m3).url_with_modifiers(url) == f'{url}?{q1}&{q2}&{q3}'
