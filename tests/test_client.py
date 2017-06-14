from unittest.mock import Mock
from urllib.parse import urlparse

import jsonschema
import pytest
import json
import os
from jsonschema import ValidationError
from jsonapi_client import ResourceTuple
import jsonapi_client.objects
import jsonapi_client.relationships
import jsonapi_client.resourceobject
from jsonapi_client.exceptions import DocumentError, AsyncError
from jsonapi_client.filter import Filter
from jsonapi_client.session import Session
from unittest import mock


external_references = \
    {'$schema': 'http://json-schema.org/draft-04/schema#',
     'properties': {'reference-id': {'type': ['string', 'null']},
                    'reference-type': {'type': ['string', 'null']},
                    'target': {'relation': 'to-one',
                               'resource': ['individuals',
                                            'products']},
                    'valid-for': {'properties': {'end-datetime': {'format': 'date-time',
                                                                  'type': ['string',
                                                                           'null']},
                                                 'start-datetime': {
                                                     'format': 'date-time',
                                                     'type': ['string', 'null']}},
                                  'required': ['start-datetime'],
                                  'type': 'object'}},
     'type': 'object'}

leases = \
    {'$schema': 'http://json-schema.org/draft-04/schema#',
     'properties': {'lease-items': {'relation': 'to-many',
                                        'resource': ['lease-items']},
                    'user-account': {'relation': 'to-one',
                                         'resource': ['user-accounts']},
                    'lease-id': {'type': ['string', 'null']},
                    'external-references': {'relation': 'to-many',
                                            'resource': ['external-references']},
                    'active-status': {'enum': ['pending', 'active', 'terminated']},
                    'parent-lease': {'relation': 'to-one',
                                         'resource': ['sales-leases']},
                    'reference-number': {'type': ['string', 'null']},
                    'related-parties': {'relation': 'to-many',
                                        'resource': ['party-relationships']},
                    'valid-for': {'properties': {'end-datetime': {'format': 'date-time',
                                                                  'type': ['string',
                                                                           'null']},
                                                 'start-datetime': {
                                                     'format': 'date-time',
                                                     'type': ['string', 'null']}},
                                  'required': ['start-datetime'],
                                  'type': 'object'}},
     'type': 'object'}

user_accounts = \
    {'$schema': 'http://json-schema.org/draft-04/schema#',
     'properties': {'account-id': {'type': ['string', 'null']},
                    'user-type': {'type': ['string', 'null']},
                    'leases': {'relation': 'to-many', 'resource': ['leases']},
                    'associated-partner-accounts': {'relation': 'to-many',
                                                    'resource': ['partner-accounts']},
                    'partner-accounts': {'relation': 'to-many',
                                         'resource': ['partner-accounts']},
                    'external-references': {'relation': 'to-many',
                                            'resource': ['external-references']},
                    'active-status': {
                        'enum': ['pending', 'active', 'inactive', 'suspended']},
                    'name': {'type': ['string', 'null']},
                    'valid-for': {'properties': {'end-datetime': {'format': 'date-time',
                                                                  'type': ['string',
                                                                           'null']},
                                                 'start-datetime': {
                                                     'format': 'date-time',
                                                     'type': ['string', 'null']}},
                                  'required': ['start-datetime'],
                                  'type': 'object'}},
     'type': 'object'}


# TODO: figure out why this is not correctly in resources-schema
leases['properties']['valid-for']['properties']['meta'] = \
     {'type': 'object', 'properties': {'type': {'type': 'string'}}}

api_schema_simple = \
    {'leases': leases}

api_schema_all = \
    {'leases': leases,
                'external-references': external_references,
                'user-accounts': user_accounts,
    }


# jsonapi.org example

articles = {
    'properties': {
        'title': {'type': 'string'},
        'author': {'relation': 'to-one', 'resource': ['people']},
        'comments': {'relation': 'to-many', 'resource': ['comments']},
        'comment-or-author': {'relation': 'to-one', 'resource': ['comments', 'people']},
        'comments-or-authors': {'relation': 'to-many', 'resource': ['comments', 'people']},
    }
}

people = {'properties': {
    'first-name': {'type': 'string'},
    'last-name': {'type': 'string'},
    'twitter': {'type': ['null', 'string']},
}}

comments = {'properties': {
    'body': {'type': 'string'},
    'author': {'relation': 'to-one', 'resource': ['people']}
}}

article_schema_all = \
    {
        'articles': articles,
        'people': people,
        'comments': comments
    }

article_schema_simple = \
    {
        'articles': articles,
    }

underscore_schema = \
    {
        'articles': {
            'properties': {
                'with_underscore': {'type': 'string'},
                'with-dash': {'type': 'string'},
            }
        }
    }


@pytest.fixture(scope='function', params=[None, article_schema_simple,
                                          article_schema_all])
def article_schema(request):
    return request.param


@pytest.fixture(scope='function', params=[None, api_schema_simple, api_schema_all])
def api_schema(request):
    return request.param


def load(filename):
    filename = filename.replace('?', '__').replace('"', '__')
    fname = os.path.join(os.path.dirname(__file__), 'json', f'{filename}.json')
    try:
        with open(fname, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise DocumentError(f'File not found: {fname}', errors=dict(status_code=404))



#mock_fetch_cm = async_mock.patch('jsonapi_client.session.fetch_json', new_callable=MockedFetch)

@pytest.fixture
def mock_req(mocker):
    m1 = mocker.patch('jsonapi_client.session.Session.http_request')
    m1.return_value = (201, {}, 'location')
    return m1


@pytest.fixture
def mock_req_async(mocker):
    rv = (201, {}, 'location')

    class MockedReqAsync(Mock):
        async def __call__(self, *args):
            super().__call__(*args)
            return rv

    m2 = mocker.patch('jsonapi_client.session.Session.http_request_async', new_callable=MockedReqAsync)
    return m2


@pytest.fixture
def mocked_fetch(mocker):
    def mock_fetch(url):
        parsed_url = urlparse(url)
        file_path = parsed_url.path[1:]
        query = parsed_url.query
        return load(f'{file_path}?{query}' if query else file_path)

    class MockedFetch:
        def __call__(self, url):
            return mock_fetch(url)

    class MockedFetchAsync:
        async def __call__(self, url):
            return mock_fetch(url)

    m1 = mocker.patch('jsonapi_client.session.Session._fetch_json', new_callable=MockedFetch)
    m2 = mocker.patch('jsonapi_client.session.Session._fetch_json_async', new_callable=MockedFetchAsync)
    return


@pytest.fixture
def mock_update_resource(mocker):
    m = mocker.patch('jsonapi_client.resourceobject.ResourceObject._update_resource')
    return m


def test_initialization(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', schema=article_schema)
    article = s.get('articles')
    assert s.resources_by_link['http://example.com/articles/1'] is \
           s.resources_by_resource_identifier[('articles', '1')]
    assert s.resources_by_link['http://example.com/comments/12'] is \
           s.resources_by_resource_identifier[('comments', '12')]
    assert s.resources_by_link['http://example.com/comments/5'] is \
           s.resources_by_resource_identifier[('comments', '5')]
    assert s.resources_by_link['http://example.com/people/9'] is \
           s.resources_by_resource_identifier[('people', '9')]


@pytest.mark.asyncio
async def test_initialization_async(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', enable_async=True, schema=article_schema)
    article = await s.get('articles')
    assert s.resources_by_link['http://example.com/articles/1'] is \
           s.resources_by_resource_identifier[('articles', '1')]
    assert s.resources_by_link['http://example.com/comments/12'] is \
           s.resources_by_resource_identifier[('comments', '12')]
    assert s.resources_by_link['http://example.com/comments/5'] is \
           s.resources_by_resource_identifier[('comments', '5')]
    assert s.resources_by_link['http://example.com/people/9'] is \
           s.resources_by_resource_identifier[('people', '9')]
    s.close()


def test_basic_attributes(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', schema=article_schema)
    doc = s.get('articles')
    assert len(doc.resources) == 2
    article = doc.resources[0]
    assert article.id == "1"
    assert article.type == "articles"
    assert article.title.startswith('JSON API paints')

    assert doc.links.self.href == 'http://example.com/articles'
    attr_set = {'title', 'author', 'comments', 'nested1', 'comment_or_author', 'comments_or_authors'}

    my_attrs = {i for i in dir(article.fields) if not i.startswith('_')}

    assert my_attrs == attr_set


@pytest.mark.asyncio
async def test_basic_attributes_async(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', enable_async=True, schema=article_schema)
    doc = await s.get('articles')
    assert len(doc.resources) == 2
    article = doc.resources[0]
    assert article.id == "1"
    assert article.type == "articles"
    assert article.title.startswith('JSON API paints')
    assert article['title'].startswith('JSON API paints')

    assert doc.links.self.href == 'http://example.com/articles'

    attr_set = {'title', 'author', 'comments', 'nested1', 'comment_or_author', 'comments_or_authors'}

    my_attrs = {i for i in dir(article.fields) if not i.startswith('_')}

    assert my_attrs == attr_set
    s.close()


def test_relationships_single(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', schema=article_schema)
    article, article2 = s.get('articles').resources
    author = article.author
    assert {i for i in dir(author.fields) if not i.startswith('_')} \
             == {'first_name', 'last_name', 'twitter'}
    assert author.type == 'people'
    assert author.id == '9'

    assert author.first_name == 'Dan'
    assert author['first-name'] == 'Dan'
    assert author.last_name == 'Gebhardt'
    assert article.relationships.author.links.self.href == "http://example.com/articles/1/relationships/author"

    author = article.author
    assert author.first_name == 'Dan'
    assert author.last_name == 'Gebhardt'
    assert author.links.self.href == "http://example.com/people/9"

    assert article.comment_or_author.id == '12'
    assert article.comment_or_author.type == 'comments'
    assert article.comment_or_author.body == 'I like XML better'

    assert article2.comment_or_author.id == '9'
    assert article2.comment_or_author.type == 'people'
    assert article2.comment_or_author.first_name == 'Dan' \

@pytest.mark.asyncio
async def test_relationships_single_async(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', enable_async=True, schema=article_schema)
    doc = await s.get('articles')
    article, article2 = doc.resources

    author = article.author
    assert isinstance(author, jsonapi_client.relationships.SingleRelationship)
    with pytest.raises(AsyncError):
        _ = author.resource

    await author.fetch()
    author_res = author.resource
    assert {i for i in dir(author_res.fields) if not i.startswith('_')} \
           == {'first_name', 'last_name', 'twitter'}
    assert author_res.type == 'people'
    assert author_res.id == '9'

    assert author_res.first_name == 'Dan'
    assert author_res.last_name == 'Gebhardt'
    assert author.links.self.href == "http://example.com/articles/1/relationships/author"

    author = article.author.resource
    assert isinstance(author, jsonapi_client.resourceobject.ResourceObject)
    assert author.first_name == 'Dan'
    assert author.last_name == 'Gebhardt'
    assert author.links.self.href == "http://example.com/people/9"

    await article.comment_or_author.fetch()
    assert article.comment_or_author.resource.id == '12'
    assert article.comment_or_author.resource.type == 'comments'
    assert article.comment_or_author.resource.body == 'I like XML better'

    await article2.comment_or_author.fetch()
    assert article2.comment_or_author.resource.id == '9'
    assert article2.comment_or_author.resource.type == 'people'
    assert article2.comment_or_author.resource.first_name == 'Dan'
    s.close()

def test_relationships_multi(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', schema=article_schema)
    article, article2 = s.get('articles').resources
    comments = article.comments
    assert len(comments) == 2
    c1, c2 = comments
    assert c1 == comments[0]
    assert c2 == comments[1]

    assert isinstance(c1, jsonapi_client.resourceobject.ResourceObject)
    assert 'body' in dir(c1)
    assert c1.body == "First!"

    assert c2.body == 'I like XML better'
    assert c2.author.id == '9'
    assert c2.author.first_name == 'Dan'
    assert c2.author.last_name == 'Gebhardt'

    res1, res2 = article.comments_or_authors
    assert res1.id == '9'
    assert res1.type == 'people'
    assert res1.first_name == 'Dan'

    assert res2.id == '12'
    assert res2.type == 'comments'
    assert res2.body == 'I like XML better'


@pytest.mark.asyncio
async def test_relationships_multi_async(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', enable_async=True, schema=article_schema)
    doc = await s.get('articles')
    article = doc.resource
    comments = article.comments
    assert isinstance(comments, jsonapi_client.relationships.MultiRelationship)
    assert len(comments._resource_identifiers) == 2

    c1, c2 = await comments.fetch()

    assert isinstance(c1, jsonapi_client.resourceobject.ResourceObject)
    assert 'body' in dir(c1)
    assert c1.body == "First!"

    assert isinstance(c1.author, jsonapi_client.relationships.SingleRelationship)

    assert c2.body == 'I like XML better'
    with pytest.raises(AsyncError):
        assert c2.author.resource.id == '9'
    await c2.author.fetch()
    author_res = c2.author.resource
    assert author_res.id == '9'
    assert author_res.first_name == 'Dan'
    assert author_res.last_name == 'Gebhardt'

    rel = article.comments_or_authors
    assert isinstance(rel, jsonapi_client.relationships.MultiRelationship)
    await rel.fetch()
    res1, res2 = rel.resources

    assert res1.id == '9'
    assert res1.type == 'people'
    assert res1.first_name == 'Dan'

    assert res2.id == '12'
    assert res2.type == 'comments'
    assert res2.body == 'I like XML better'

    s.close()


def test_fetch_external_resources(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', schema=article_schema)
    article = s.get('articles').resource
    comments = article.comments
    session = article.session
    c1, c2 = comments
    assert c1.body == "First!"
    assert len(session.resources_by_resource_identifier) == 5
    assert len(session.resources_by_link) == 5
    assert len(session.documents_by_link) == 1
    assert c1.author.id == "2"
    assert len(session.resources_by_resource_identifier) == 6
    assert len(session.resources_by_link) == 6
    assert len(session.documents_by_link) == 2

    assert c1.author.type == "people"

    # fetch external content
    assert c1.author.first_name == 'Dan 2'
    assert c1.author.last_name == 'Gebhardt 2'


@pytest.mark.asyncio
async def test_fetch_external_resources_async(mocked_fetch, article_schema):
    s = Session('http://localhost:8080', enable_async=True, schema=article_schema)
    doc = await s.get('articles')
    article = doc.resource
    comments = article.comments
    assert isinstance(comments, jsonapi_client.relationships.MultiRelationship)
    session = article.session
    c1, c2 = await comments.fetch()
    assert c1.body == "First!"
    assert len(session.resources_by_resource_identifier) == 5
    assert len(session.resources_by_link) == 5
    assert len(session.documents_by_link) == 1

    with pytest.raises(AsyncError):
        _ = c1.author.resource.id
    await c1.author.fetch()
    # fetch external content
    c1_author = c1.author.resource
    assert c1_author.id == "2"
    assert len(session.resources_by_resource_identifier) == 6
    assert len(session.resources_by_link) == 6
    assert len(session.documents_by_link) == 2

    assert c1_author.type == "people"
    assert c1_author.first_name == 'Dan 2'
    assert c1_author.last_name == 'Gebhardt 2'
    s.close()

def test_error_404(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/api', schema=api_schema)
    documents = s.get('leases')
    d1 = documents.resources[1]

    parent_lease = d1.relationships.parent_lease
    assert isinstance(parent_lease, jsonapi_client.relationships.LinkRelationship)
    with pytest.raises(DocumentError) as e:
        assert parent_lease.resource.active_status == 'active'
    assert e.value.errors['status_code'] == 404

    with pytest.raises(DocumentError) as e:
        s.get('error')

    assert 'Error document was fetched' in str(e)


@pytest.mark.asyncio
async def test_error_404_async(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/api', enable_async=True, schema=api_schema)
    documents = await s.get('leases')
    d1 = documents.resources[1]

    parent_lease = d1.parent_lease
    assert isinstance(parent_lease, jsonapi_client.relationships.LinkRelationship)
    with pytest.raises(AsyncError):
        _ = parent_lease.resource.active_status

    with pytest.raises(DocumentError) as e:
        res = await parent_lease.fetch()

    assert e.value.errors['status_code'] == 404
    with pytest.raises(DocumentError) as e:
        await s.get('error')
    assert 'Error document was fetched' in str(e)
    s.close()


def test_relationships_with_context_manager(mocked_fetch, api_schema):
    with Session('http://localhost:8080/api', schema=api_schema) as s:
        documents = s.get('leases')
        d1 = documents.resources[0]

        assert d1.lease_id is None
        assert d1.id == 'qvantel-lease1'
        assert d1.type == 'leases'
        assert d1.active_status == d1.fields.active_status == 'active'
        assert d1.valid_for.start_datetime == "2015-07-06T12:23:26.000Z"
        assert d1['valid-for']['start-datetime'] == "2015-07-06T12:23:26.000Z"
        assert d1.valid_for.meta.type == 'valid-for-datetime'
        dird = dir(d1)
        assert 'external_references' in dird

        # Relationship collection (using link rather than ResourceObject)
        # fetches http://localhost:8080/api/leases/qvantel-lease1/external-references
        assert len(d1.external_references) == 1

        ext_ref = d1.external_references[0]
        assert ext_ref.reference_id == ext_ref.fields.reference_id == '0123015150'
        assert ext_ref.id == 'qvantel-lease1-extref'
        assert ext_ref.type == 'external-references'

        ext_ref = d1.external_references[0]
        assert isinstance(ext_ref, jsonapi_client.resourceobject.ResourceObject)

        assert ext_ref.reference_id == '0123015150'
        assert ext_ref.id == 'qvantel-lease1-extref'
        assert ext_ref.type == 'external-references'

        assert 'user_account' in dird
        assert d1.user_account.id == 'qvantel-useraccount1'
        #assert isinstance(d1.user_account,
        assert d1.user_account.type == 'user-accounts'
        assert d1.links.self.href == '/api/leases/qvantel-lease1'

        # Single relationship (using link rather than ResourceObject)
        # Fetches http://localhost:8080/api/leases/qvantel-lease1/parent-lease
        parent_lease = d1.parent_lease
        #assert isinstance(parent_lease, jsonapi_client.relationships.LinkRelationship)
        # ^ Anything is not fetched yet
        if api_schema:
            assert parent_lease.active_status == 'active'
        else:
            assert parent_lease[0].active_status == 'active'
        # ^ now parent lease is fetched, but attribute access goes through Relationship
    assert not s.resources_by_link
    assert not s.resources_by_resource_identifier
    assert not s.documents_by_link


@pytest.mark.asyncio
async def test_relationships_with_context_manager_async_async(mocked_fetch, api_schema):
    async with Session('http://localhost:8080/api', schema=api_schema, enable_async=True) as s:
        documents = await s.get('leases')
        d1 = documents.resources[0]

        assert d1.lease_id is None
        assert d1.id == 'qvantel-lease1'
        assert d1.type == 'leases'
        assert d1.active_status == d1.fields.active_status == 'active'
        assert d1.valid_for.start_datetime == "2015-07-06T12:23:26.000Z"
        assert d1['valid-for']['start-datetime'] == "2015-07-06T12:23:26.000Z"
        assert d1.valid_for.meta.type == 'valid-for-datetime'
        dird = dir(d1)
        assert 'external_references' in dird

        ext_refs = d1.external_references
        ext_ref_res = (await ext_refs.fetch())[0]

        assert ext_ref_res.reference_id == ext_ref_res.fields.reference_id == '0123015150'
        assert ext_ref_res.id == 'qvantel-lease1-extref'
        assert ext_ref_res.type == 'external-references'

        assert isinstance(ext_ref_res, jsonapi_client.resourceobject.ResourceObject)

        assert ext_ref_res.reference_id == '0123015150'
        assert ext_ref_res.id == 'qvantel-lease1-extref'
        assert ext_ref_res.type == 'external-references'

        assert 'user_account' in dird
        await d1.user_account.fetch()
        assert d1.user_account.resource.id == 'qvantel-useraccount1'
        assert d1.user_account.resource.type == 'user-accounts'
        assert d1.links.self.href == '/api/leases/qvantel-lease1'

        await d1.parent_lease.fetch()
        parent_lease = d1.parent_lease.resource
        assert parent_lease.active_status == 'active'

    assert not s.resources_by_link
    assert not s.resources_by_resource_identifier
    assert not s.documents_by_link


def test_more_relationships(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/api', schema=api_schema)
    documents = s.get('leases')
    d1 = documents.resources[0]

    assert d1.lease_id is None
    assert d1.id == 'qvantel-lease1'
    assert d1.type == 'leases'
    assert d1.active_status == d1.fields.active_status == 'active'
    assert d1.valid_for.start_datetime == "2015-07-06T12:23:26.000Z"
    assert d1.valid_for.meta.type == 'valid-for-datetime'
    dird = dir(d1)
    assert 'external_references' in dird

    # Relationship collection (using link rather than ResourceObject)
    # fetches http://localhost:8080/api/leases/qvantel-lease1/external-references
    assert len(d1.external_references) == 1

    ext_ref = d1.external_references[0]
    assert ext_ref.reference_id == ext_ref.fields.reference_id == '0123015150'
    assert ext_ref.id == 'qvantel-lease1-extref'
    assert ext_ref.type == 'external-references'

    ext_ref = d1.external_references[0]
    assert isinstance(ext_ref, jsonapi_client.resourceobject.ResourceObject)

    assert ext_ref.reference_id == '0123015150'
    assert ext_ref.id == 'qvantel-lease1-extref'
    assert ext_ref.type == 'external-references'

    assert 'user_account' in dird
    assert d1.user_account.id == 'qvantel-useraccount1'
    assert d1.user_account.type == 'user-accounts'
    assert d1.links.self.href == '/api/leases/qvantel-lease1'

    # Single relationship (using link rather than ResourceObject)
    # Fetches http://localhost:8080/api/leases/qvantel-lease1/parent-lease
    parent_lease = d1.parent_lease
    # ^ Anything is not fetched yet
    if api_schema:
        assert parent_lease.active_status == 'active'
    else:
        assert parent_lease[0].active_status == 'active'
    # ^ now parent lease is fetched, but attribute access goes through Relationship


@pytest.mark.asyncio
async def test_more_relationships_async_fetch(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/api', enable_async=True, schema=api_schema)
    documents = await s.get('leases')
    d1 = documents.resources[0]
    dird = dir(d1)

    assert 'external_references' in dird

    # Relationship collection (using link rather than ResourceObject)
    # fetches http://localhost:8080/api/leases/qvantel-lease1/external-references

    ext_ref = d1.external_references
    assert isinstance(ext_ref, jsonapi_client.relationships.LinkRelationship)

    with pytest.raises(AsyncError):
        len(ext_ref.resources) == 1

    with pytest.raises(AsyncError):
        _ = ext_ref.resources.reference_id

    ext_ref_res = (await ext_ref.fetch())[0]

    assert ext_ref_res.reference_id == '0123015150'

    assert ext_ref_res.id == 'qvantel-lease1-extref'
    assert ext_ref_res.type == 'external-references'

    ext_ref = d1.external_references.resources[0]
    assert isinstance(ext_ref, jsonapi_client.resourceobject.ResourceObject)

    assert ext_ref.reference_id == '0123015150'
    assert ext_ref.id == 'qvantel-lease1-extref'
    assert ext_ref.type == 'external-references'

    assert 'user_account' in dird
    await d1.user_account.fetch()
    assert d1.user_account.resource.id == 'qvantel-useraccount1'
    assert d1.user_account.resource.type == 'user-accounts'
    assert d1.links.self.href == '/api/leases/qvantel-lease1'

    # Single relationship (using link rather than ResourceObject)
    # Fetches http://localhost:8080/api/leases/qvantel-lease1/parent-lease
    parent_lease = d1.parent_lease
    assert isinstance(parent_lease, jsonapi_client.relationships.LinkRelationship)
    # ^ Anything is not fetched yet
    await parent_lease.fetch()
    assert parent_lease.resource.active_status == 'active'
    # ^ now parent lease is fetched, but attribute access goes through Relationship
    s.close()

class SuccessfullResponse:
    status_code = 200
    headers = {}
    content = ''
    @classmethod
    def json(cls):
        return {}


def test_patching(mocker, mocked_fetch, api_schema, mock_update_resource):
    mock_patch = mocker.patch('requests.request')
    mock_patch.return_value = SuccessfullResponse

    s = Session('http://localhost:80801/api', schema=api_schema)
    documents = s.get('leases').resources

    # if single document (not collection) we must also be able to
    # set attributes of main resourceobject directly
    # TODO test this^

    assert len(documents) == 4
    with pytest.raises(AttributeError):
        documents.someattribute = 'something'

    d1 = documents[0]

    # Let's change fields in resourceobject
    assert d1.active_status == 'active'
    d1.active_status = 'terminated'
    assert d1.is_dirty
    assert s.is_dirty
    assert 'active-status' in d1.dirty_fields
    d1.commit()  # alternatively s.commit() which does commit for all dirty objects
    assert len(d1.dirty_fields) == 0
    assert not d1.is_dirty
    assert not s.is_dirty

    assert d1.valid_for.start_datetime == "2015-07-06T12:23:26.000Z"

    d1.valid_for.start_datetime = 'something-else'
    d1.valid_for.new_field = 'something-new'
    assert d1.valid_for.is_dirty
    assert 'start-datetime' in d1.valid_for._dirty_attributes
    assert d1.is_dirty
    assert 'valid-for' in d1.dirty_fields

    assert d1._attributes.diff == {'valid-for': {'start-datetime': 'something-else',
                                                       'new-field': 'something-new'}}

    assert d1.external_references[0].id == 'qvantel-lease1-extref'

    assert len(d1.external_references) == 1

    add_resources = [ResourceTuple(str(i), 'external-references') for i in [1,2]]
    d1.external_references += add_resources

    assert len(d1.relationships.external_references.document.resources) == 1 # Document itself should not change
    assert len(d1.external_references) == 3

    d1.external_references += [ResourceTuple('3', 'external-references')]
    assert len(d1.relationships.external_references.document.resources) == 1 # Document itself should not change
    assert len(d1.external_references) == 4
    assert d1.relationships.external_references.is_dirty
    assert len(mock_patch.mock_calls) == 1
    d1.commit()
    assert len(mock_patch.mock_calls) == 2
    actual_data = mock_patch.mock_calls[1][2]['json']['data']
    expected_data = {
        'id': 'qvantel-lease1',
        'type': 'leases',
        'attributes': {
            'valid-for': {'new-field': 'something-new',
                          'start-datetime': 'something-else'}},
        'relationships': {
            'external-references': {
                'data': [
                    {'id': 'qvantel-lease1-extref',
                     'type': 'external-references'},
                    {'id': '1',
                     'type': 'external-references'},
                    {'id': '2',
                     'type': 'external-references'},
                    {'id': '3',
                     'type': 'external-references'}
                     ]}}}
    assert actual_data == expected_data
    assert not d1.is_dirty
    assert not d1.valid_for.is_dirty
    assert not d1.relationships.external_references.is_dirty
    # After commit we receive new data from the server, and everything should be as expected again


def test_result_pagination(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/', schema=api_schema)

    agr_pages = []
    doc = s.get('test_leases')
    agr1 = doc.resources[0]

    agr_pages.append(agr1)

    # Pagination of collection
    assert len(doc.resources) == 2  # length of received collection

    agr_next = doc.links.next.fetch()
    while agr_next:
        agr_pages.append(agr_next)
        assert len(agr_next.resources) == 2
        agr_prev = agr_next
        agr_cur = agr_next
        agr_next = agr_next.links.next.fetch()
        if agr_next:
            assert agr_next.links.prev == agr_prev.links.self

    assert agr_cur.links.self == doc.links.last
    assert agr_cur.links.first == doc.links.self == doc.links.first

    d1 = doc.resources[0]
    ext_refs = d1.external_references

    assert len(ext_refs) == 2

    ext_refs2 = d1.relationships.external_references.document.links.next.fetch()
    assert len(ext_refs2.resources) == 2
    assert d1.relationships.external_references.document.links.last == ext_refs2.links.self


def test_result_pagination_iteration(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/', schema=api_schema)

    leases = list(s.iterate('test_leases'))
    assert len(leases) == 6
    for l in range(len(leases)):
        assert leases[l].id == str(l+1)


@pytest.mark.asyncio
async def test_result_pagination_iteration_async(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/', schema=api_schema, enable_async=True)

    leases = [r async for r in s.iterate('test_leases')]
    assert len(leases) == 6
    for l in range(len(leases)):
        assert leases[l].id == str(l+1)
    s.close()


def test_result_filtering(mocked_fetch, api_schema):
    s = Session('http://localhost:8080/', schema=api_schema)

    result = s.get('test_leases', Filter(title='Dippadai'))
    result2 = s.get('test_leases', Filter(f'filter[title]="Dippadai"'))

    assert result == result2

    d1 = result.resources[0]
    ext_refs = d1.relationships.external_references

    result = ext_refs.filter(Filter(title='Hep'))

    assert len(result.resources) == 1


article_test_schema = \
    {
        'articles': {
            'properties': {
                'title': {'type': 'string'},
                'extra-attribute': {'type': ['string', 'null']},
                'nested1': {'type': 'object', 'properties':
                    {
                        'other': {'type': ['string', 'null']},
                        'nested':
                            {'type': 'object', 'properties':
                                {'name': {'type': 'string'},
                                 'other': {'type': ['string', 'null']},
                                 }}}},
                'nested2': {'type': 'object', 'properties':
                    {
                        'other': {'type': ['null', 'string']},
                        'nested':
                            {'type': 'object', 'properties':
                                {'name': {'type': ['null', 'string'],
                                          'other': {'type': ['string', 'null']},
                                          }}}}}
            },
        }
    }


def test_attribute_checking_from_schema(mocked_fetch):

    s = Session('http://localhost:8080/', schema=article_test_schema)
    article = s.get('articles').resource
    assert article.title.startswith('JSON API paints')

    # Extra attribute that is in schema but not in data
    assert article.extra_attribute is None
    with pytest.raises(AttributeError):
        attr = article.extra_attribute_2

    # nested1 is in the test data
    with pytest.raises(AttributeError):
        attr = article.nested1.nested.a
    with pytest.raises(AttributeError):
        attr = article.nested1.a
    with pytest.raises(AttributeError):
        attr = article.a
    assert article.nested1.nested.name == 'test'
    assert article.nested1.nested.other is None
    assert article.nested1.other is None

    # nested2 is not in the test data
    with pytest.raises(AttributeError):
        attr = article.nested2.nested.a
    with pytest.raises(AttributeError):
        attr = article.nested2.a

    assert len(article.nested2) == 2  # There are still the items that were specified in schema

    assert article.nested2.nested.name is None
    assert len(article.nested2.nested) == 1


def test_schema_validation(mocked_fetch):
    schema2 = article_test_schema.copy()
    schema2['articles']['properties']['title']['type'] = 'number'
    s = Session('http://localhost:8080/', schema=schema2)

    with pytest.raises(ValidationError) as e:
        article = s.get('articles')
        #article.title.startswith('JSON API paints')
    assert 'is not of type \'number\'' in str(e)


def make_patch_json(ids, type_, field_name=None):
    if isinstance(ids, list):
        if isinstance(ids[0], tuple):
            content = {'data': [{'id': str(i), 'type': str(j)} for i, j in ids]}
        else:
            content = {'data': [{'id': str(i), 'type': type_} for i in ids]}
    else:
        content = {'data': {'id': str(ids), 'type': type_}}

    data = {'data': {'type': 'articles',
                     'id': '1',
                     'attributes': {},
                     'relationships':
                         {
                             field_name or type_: content
                         }}}
    return data

def test_posting_successfull(mock_req):
    s = Session('http://localhost:80801/api', schema=api_schema_all)
    a = s.create('leases')
    assert a.is_dirty
    a.lease_id = '1'
    a.active_status = 'pending'
    a.reference_number = 'test'
    a.valid_for.start_datetime = 'asdf'

    with mock.patch('jsonapi_client.session.Session.read'):
        a.commit()

    agr_data = \
        {'data': {'type': 'leases',
                  'attributes': {'lease-id': '1',
                                 'active-status': 'pending',
                                 'reference-number': 'test',
                                 'valid-for': {'start-datetime': 'asdf'},
                                 },
                  'relationships': {}}}

    mock_req.assert_called_once_with('post', 'http://localhost:80801/api/leases',
                                     agr_data)


@pytest.mark.asyncio
async def test_posting_successfull_async(mock_req_async, mock_update_resource):
    s = Session('http://localhost:80801/api', schema=api_schema_all, enable_async=True)
    a = s.create('leases')
    assert a.is_dirty
    a.lease_id = '1'
    a.active_status = 'pending'
    a.reference_number = 'test'
    a.valid_for.start_datetime = 'asdf'
    await a.commit()

    agr_data = \
        {'data': {'type': 'leases',
                  'attributes': {'lease-id': '1', 'active-status': 'pending',
                                 'reference-number': 'test',
                                 'valid-for': {'start-datetime': 'asdf'},
                                 },
                  'relationships': {}}}


    mock_req_async.assert_called_once_with('post', 'http://localhost:80801/api/leases',
                                     agr_data)
    s.close()

@pytest.mark.parametrize('commit', [0, 1])
@pytest.mark.parametrize('kw_format', [0, 1])
def test_posting_successfull_with_predefined_fields(kw_format, commit, mock_req, mocker):
    mocker.patch('jsonapi_client.session.Session.read')
    s = Session('http://localhost:80801/api', schema=api_schema_all)

    kwargs1 = dict(valid_for__start_datetime='asdf')
    kwargs2 = dict(valid_for={'start-datetime':'asdf'})

    a = s.create('leases',
                 lease_id='1',
                 active_status='pending',
                 reference_number='test',
                 lease_items=['1'],
                 **kwargs1 if kw_format else kwargs2
                 )
    if commit:
        a.commit()
    assert a.is_dirty != commit

    if not commit:
        with mock.patch('jsonapi_client.session.Session.read'):
            a.commit()

    agr_data = \
        {'data': {'type': 'leases',
                  'attributes': {'lease-id': '1', 'active-status': 'pending',
                                 'reference-number': 'test',
                                 'valid-for': {'start-datetime': 'asdf'},
                                 },
                  'relationships': {'lease-items': {'data': [{'id': '1',
                                                        'type': 'lease-items'}]},
                                    }}}

    mock_req.assert_called_once_with('post', 'http://localhost:80801/api/leases',
                                     agr_data)


def test_create_with_underscore(mock_req):
    s = Session('http://localhost:8080/', schema=underscore_schema)
    a = s.create('articles',
                 fields={'with-dash': 'test', 'with_underscore': 'test2'}
    )
    assert 'with_underscore' in a._attributes
    assert 'with-dash' in a._attributes

    with mock.patch('jsonapi_client.session.Session.read'):
        a.commit()


def test_create_with_underscore2(mock_req):
    s = Session('http://localhost:8080/', schema=underscore_schema)
    a = s.create('articles', with_dash='test',
                 fields={'with_underscore': 'test2'}
    )
    assert 'with_underscore' in a._attributes
    assert 'with-dash' in a._attributes

    with mock.patch('jsonapi_client.session.Session.read'):
        a.commit()


def test_posting_relationships(mock_req, article_schema):
    if not article_schema:
        return

    s = Session('http://localhost:8080/', schema=article_schema)
    a = s.create('articles',
            title='Test article',
            comments=[ResourceTuple(i, 'comments') for i in ('5', '12')],
            author=ResourceTuple('9', 'people'),
            comments_or_authors=[ResourceTuple('9', 'people'), ResourceTuple('12', 'comments')]
    )
    with mock.patch('jsonapi_client.session.Session.read'):
        a.commit()


def test_posting_successfull_without_schema(mock_req):
    s = Session('http://localhost:80801/api')
    a = s.create('leases')

    a.lease_id = '1'
    a.active_status = 'pending'
    a.reference_number = 'test'

    a.create_map('valid_for') # Without schema we need to do this manually

    a.valid_for.start_datetime = 'asdf'
    a.commit()

    agr_data = \
        {'data': {'type': 'leases',
                  'attributes': {'lease-id': '1', 'active-status': 'pending',
                                 'reference-number': 'test',
                                 'valid-for': {'start-datetime': 'asdf'}},
                  'relationships': {}}}

    mock_req.assert_called_once_with('post', 'http://localhost:80801/api/leases',
                                     agr_data)

@pytest.mark.asyncio
async def test_posting_successfull_without_schema(mock_req_async, mock_update_resource):
    s = Session('http://localhost:80801/api', enable_async=True)
    a = s.create('leases')

    a.lease_id = '1'
    a.active_status = 'pending'
    a.reference_number = 'test'

    a.create_map('valid_for')  # Without schema we need to do this manually

    a.valid_for.start_datetime = 'asdf'
    await a.commit()

    agr_data = \
        {'data': {'type': 'leases',
                  'attributes': {'lease-id': '1', 'active-status': 'pending',
                                 'reference-number': 'test',
                                 'valid-for': {'start-datetime': 'asdf'}},
                  'relationships': {}}}

    mock_req_async.assert_called_once_with('post', 'http://localhost:80801/api/leases',
                                     agr_data)
    s.close()

def test_posting_post_validation_error():
    s = Session('http://localhost:80801/api', schema=api_schema_all)
    a = s.create('leases')
    a.lease_id = '1'
    a.active_status = 'blah'
    a.reference_number = 'test'
    a.valid_for.start_datetime='asdf'
    with pytest.raises(jsonschema.ValidationError):
        a.commit()


def test_relationship_manipulation(mock_req, article_schema, mocked_fetch, mock_update_resource):
    s = Session('http://localhost:80801/', schema=article_schema)
    article, article2 = s.get('articles').resources
    assert article.relationships.author.resource.id == '9'
    if article_schema:
        assert article.relationships.author.type == 'people'
    # article.author = '10' # assigning could be done directly.
    # This would go through ResourceObject.__setattr__ and
    # through RelationshipDict.__setattr__, where it goes to
    # Relationship.set() method
    # But does pycharm get confused with this style?

    if article_schema:
        article.relationships.author = '10'  # to one.
    else:
        article.relationships.author.set('10', 'people')
    assert article.relationships.author.is_dirty
    assert 'author' in article.dirty_fields

    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json('10', 'people', 'author'))
    mock_req.reset_mock()
    assert not article.dirty_fields
    assert not article.relationships.author.is_dirty

    assert article.relationships.author._resource_identifier.id == '10'
    if article_schema:
        assert article.relationships.comments.type == 'comments'
        article.relationships.comments = ['5', '6']  # to many
    else:
        with pytest.raises(TypeError):
            article.relationships.comments = ['5', '6']

        article.relationships.comments.set(['5', '6'], 'comments')  # to many

    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([5, 6], 'comments'))
    mock_req.reset_mock()

    assert [i.id for i in article.relationships.comments._resource_identifiers] == ['5', '6']

    # Test .fields attribute proxy
    article.relationships.comments.set(['6', '7'], 'comments')
    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7], 'comments'))
    mock_req.reset_mock()

    assert [i.id for i in article.relationships.comments._resource_identifiers] == ['6', '7']

    if article_schema:
        article.relationships.comments.add('8')  # id is sufficient as we know the type from schema
    else:
        with pytest.raises(TypeError):
            article.relationships.comments.add('8')  # id is sufficient as we know the type from schema
        article.relationships.comments.add('8', 'comments')
    article.relationships.comments.add('9', 'comments')  # But we can supply also type just in case we don't have schema available
    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7, 8, 9], 'comments'))
    mock_req.reset_mock()

    #assert article.relationships.comments == ['6', '7', '8', '9']
    if article_schema:
        article.relationships.comments.add(['10','11'])
    else:
        with pytest.raises(TypeError):
            article.relationships.comments.add(['10','11'])
        article.relationships.comments.add(['10', '11'], 'comments')
    #assert article.relationships.comments == ['6', '7', '8', '9', '10', '11']
    article.commit()

    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7, 8, 9, 10, 11],
                                                           'comments'))
    mock_req.reset_mock()
    comment = article.comment_or_author
    assert comment.type == 'comments'
    article.relationships.comment_or_author.set('12', 'comments')
    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json('12', 'comments', 'comment-or-author'))


    mock_req.reset_mock()
    author, comment = article.comments_or_authors
    assert comment.type == 'comments'
    assert author.type == 'people'

    rel = article.relationships.comments_or_authors
    rel.clear()
    rel.add('5', 'comments')
    rel.add('2', 'people')

    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
        make_patch_json([('5', 'comments'), ('2', 'people')], None, 'comments-or-authors'))


    mock_req.reset_mock()
    article.relationships.comments_or_authors = [
        ResourceTuple('5', 'comments'), ResourceTuple('2', 'people')]

    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
        make_patch_json([('5', 'comments'), ('2', 'people')], None, 'comments-or-authors'))


@pytest.mark.asyncio
async def test_relationship_manipulation_async(mock_req_async, mocked_fetch, article_schema, mock_update_resource):
    s = Session('http://localhost:80801/', schema=article_schema, enable_async=True)

    doc = await s.get('articles')
    article = doc.resource

    assert article.author._resource_identifier.id == '9'
    if article_schema:
        assert article.author.type == 'people'
    # article.author = '10' # assigning could be done directly.
    # This would go through ResourceObject.__setattr__ and
    # through RelationshipDict.__setattr__, where it goes to
    # Relationship.set() method
    # But does pycharm get confused with this style?

    if article_schema:
        article.author = '10'  # to one.
    else:
        article.author.set('10', 'people')
    assert article.author.is_dirty == True
    assert 'author' in article.dirty_fields

    await article.commit()
    mock_req_async.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json('10', 'people', field_name='author'))
    mock_req_async.reset_mock()
    assert not article.dirty_fields
    assert not article.author.is_dirty

    #assert article.author.value == '10'
    if article_schema:
        assert article.comments.type == 'comments'
        article.comments = ['5', '6']  # to many
    else:
        with pytest.raises(TypeError):
            article.comments = ['5', '6']

        article.comments.set(['5', '6'], 'comments')  # to many

    assert article.comments.is_dirty
    await article.commit()
    mock_req_async.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([5, 6], 'comments'))
    mock_req_async.reset_mock()

    #assert article.comments.value == ['5', '6']

    # Test .fields attribute proxy
    article.fields.comments.set(['6', '7'], 'comments')
    await article.commit()
    mock_req_async.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7], 'comments'))
    mock_req_async.reset_mock()

    #assert article.comments.value == ['6', '7']

    if article_schema:
        article.comments.add('8')  # id is sufficient as we know the type from schema
    else:
        with pytest.raises(TypeError):
            article.comments.add('8')  # id is sufficient as we know the type from schema
        article.comments.add('8', 'comments')
    article.comments.add('9', 'comments')  # But we can supply also type just in case we don't have schema available
    await article.commit()
    mock_req_async.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7, 8, 9], 'comments'))
    mock_req_async.reset_mock()

    #assert article.comments.value == ['6', '7', '8', '9']
    if article_schema:
        article.comments.add(['10','11'])
    else:
        with pytest.raises(TypeError):
            article.comments.add(['10','11'])
        article.comments.add(['10', '11'], 'comments')
    #assert article.comments.value == ['6', '7', '8', '9', '10', '11']
    await article.commit()

    mock_req_async.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7, 8, 9, 10, 11],
                                                           'comments'))
    mock_req_async.reset_mock()
    s.close()

def test_relationship_manipulation_alternative_api(mock_req, mocked_fetch, article_schema, mock_update_resource):
    s = Session('http://localhost:80801/', schema=article_schema)
    article = s.get('articles').resource

    # Test alternative direct setting attribute via RelationshipDict's __setattr__
    # This does not look very nice with 'clever' IDE that gets totally confused about
    # this.

    oc1, oc2 = article.comments

    if article_schema:
        assert article.relationships.comments.type == 'comments'
        article.comments = ['5', '6']  # to many
    else:
        with pytest.raises(TypeError):
            article.relationships.comments = ['5', '6']
        with pytest.raises(TypeError):
            article.comments = ['5', '6']
        article.comments = [ResourceTuple(i, 'comments') for i in ['5', '6']]



    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([5, 6], 'comments'))
    mock_req.reset_mock()

    #assert article.relationships.comments.value == ['5', '6']

    # ***** #
    if article_schema:
        assert article.relationships.comments.type == 'comments'
        article.comments = ['6', '7']  # to many
    else:
        with pytest.raises(TypeError):
            article.relationships.comments = ['6', '7']
        with pytest.raises(TypeError):
            article.comments = ['5', '6']
        #article.relationships.comments.set(['6', '7'], 'comments')
        article.comments = [ResourceTuple(i, 'comments') for i in ['6', '7']]


    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([6, 7], 'comments'))
    mock_req.reset_mock()

    #assert article.relationships.comments.value == ['6', '7']

    # Set resourceobject

    if article_schema:
        assert article.relationships.comments.type == 'comments'
        article.comments = oc1, oc2
    else:
        article.relationships.comments = oc1, oc2
        article.comments = oc1, oc2


    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([oc1.id, oc2.id], 'comments'))
    mock_req.reset_mock()

    #assert article.relationships.comments.value == [str(i) for i in [oc1.id, oc2.id]]


    # Let's test also .fields AttributeProxy
    if article_schema:
        assert article.relationships.comments.type == 'comments'
        article.fields.comments = ['7', '6']  # to many
    else:
        with pytest.raises(TypeError):
            article.fields.comments = ['7', '6']
        article.relationships.comments.set(['7', '6'], 'comments')

    article.commit()
    mock_req.assert_called_once_with('patch', 'http://example.com/articles/1',
                                     make_patch_json([7, 6], 'comments'))
    mock_req.reset_mock()

    #assert article.relationships.comments.value == ['7', '6']





