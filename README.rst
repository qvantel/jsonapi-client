.. image:: https://travis-ci.org/qvantel/jsonapi-client.svg?branch=master
   :target: https://travis-ci.org/qvantel/jsonapi-client

.. image:: https://coveralls.io/repos/github/qvantel/jsonapi-client/badge.svg
   :target: https://coveralls.io/github/qvantel/jsonapi-client

.. image:: https://img.shields.io/pypi/v/jsonapi-client.svg
   :target: https://pypi.python.org/pypi/jsonapi-client

.. image:: https://img.shields.io/pypi/pyversions/jsonapi-client.svg
   :target: https://pypi.python.org/pypi/jsonapi-client

.. image:: https://img.shields.io/badge/licence-BSD%203--clause-blue.svg
   :target: https://github.com/qvantel/jsonapi-client/blob/master/LICENSE.txt

==========================
JSON API client for Python
==========================

Introduction
============

Package repository: https://github.com/qvantel/jsonapi-client

This Python (3.6+) library provides easy-to-use, pythonic, ORM-like access to
JSON API ( http://jsonapi.org )

 - Optional asyncio implementation
 - Optional model schema definition and validation (=> easy reads even without schema)
 - Resource caching within session


Installation
============

From Pypi::

    pip install jsonapi-client

Or from sources::

    ./setup.py install


Usage
=====

Client session
--------------

.. code-block:: python

   from jsonapi_client import Session, Filter, ResourceTuple

   s = Session('http://localhost:8080/')
   # To start session in async mode
   s = Session('http://localhost:8080/', enable_async=True)

   # You can also pass extra arguments that are passed directly to requests or aiohttp methods,
   # such as authentication object
   s = Session('http://localhost:8080/',
               request_kwargs=dict(auth=HttpBasicAuth('user', 'password'))


   # You can also use Session as a context manager. Changes are committed in the end
   # and session is closed.
   with Session(...) as s:
       your code

   # Or with enable_async=True
   async with Session(..., enable_async=True):
       your code

   # If you are not using context manager, you need to close session manually
   s.close()

   # Fetching documents
   documents = s.get('resource_type')
   # Or if you want only 1, then
   documents = s.get('resource_type', 'id_of_document')

   # AsyncIO the same but remember to await:
   documents = await s.get('resource_type')

Filtering
---------

.. code-block:: python

   # You need first to specify your filter instance.
   # - filtering with two criteria (and)
   filter = Filter(attribute='something', attribute2='something_else')
   # - filtering some-dict.some-attr == 'something'
   filter = Filter(some_dict__some_attr='something'))
   # - filtering manually with your server syntax.
   filter = Filter('filter[post]=1&filter[author]=2')

   # If you have different URL schema for filtering, you can implement your own Filter
   # class (derive it from Filter and reimplement format_filter_query).

   # Then fetch your filtered document
   filtered = s.get('resource_type', filter) # AsyncIO with await

   # To access resources included in document:
   r1 = document.resources[0]  # first ResourceObject of document.
   r2 = document.resource      # if there is only 1 resource we can use this

Pagination
----------

.. code-block:: python

   # Pagination links can be accessed via Document object.
   next_doc = document.links.next.fetch()
   # AsyncIO
   next_doc = await document.links.next.fetch()

   # Iteration through results (uses pagination):
   for r in s.iterate('resource_type'):
       print(r)

   # AsyncIO:
   async for r in s.iterate('resource_type'):
       print(r)

Resource attribute and relationship access
------------------------------------------

.. code-block:: python

   # - attribute access
   attr1 = r1.some_attr
   nested_attr = r1.some_dict.some_attr
   #   Attributes can always also be accessed via __getitem__:
   nested_attr = r1['some-dict']['some-attr']

   # If there is namespace collision, you can also access attributes via .fields proxy
   # (both attributes and relationships)
   attr2 = r1.fields.some_attr

   # - relationship access.
   #   * Sync, this gives directly ResourceObject
   rel = r1.some_relation
   attr3 = r1.some_relation.some_attr  # Relationship attribute can be accessed directly

   #   * AsyncIO, this gives Relationship object instead because we anyway need to
   #     call asynchronous fetch function.
   rel = r1.some_relation
   #     To access ResourceObject you need to first fetch content
   await r1.some_relation.fetch()
   #     and then you can access associated resourceobject
   res = r1.some_relation.resource
   attr3 = res.some_attr  # Attribute access through ResourceObject

   # If you need to access relatinoship object itself (with sync API), you can do it via
   # .relationships proxy. For example, if you are interested in links or metadata
   # provided within relationship, or intend to manipulate relationship.
   rel_obj = r1.relationships.relation_name

Resource updating
-----------------

.. code-block:: python

   # Updating / patching existing resources
   r1.some_attr = 'something else'
   # Patching element in nested json
   r1.some_dict.some_dict.some_attr = 'something else'

   # change relationships, to-many. Accepts also iterable of ResourceObjects/
   # ResourceIdentifiers/ResourceTuples
   r1.comments = ['1', '2']
   # or if resource type is not known or can have multiple types of resources
   r1.comments_or_people = [ResourceTuple('1', 'comments'), ResourceTuple('2', 'people')]
   # or if you want to add some resources you can
   r1.comments_or_people += [ResourceTuple('1', 'people')]
   r1.commit()

   # change to-one relationships
   r1.author = '3'  # accepts also ResourceObjects/ResourceIdentifiers/ResourceTuple
   # or resource type is not known (via schema etc.)
   r1.author = ResourceTuple('3', 'people')

   # Committing changes (PATCH request)
   r1.commit(meta={'some_meta': 'data'})  # Resource committing supports optional meta data
   # AsyncIO
   await r1.commit(meta={'some_meta': 'data'})


Creating new resources
----------------------


.. code-block:: python

   # Creating new resources. Schema must be given. Accepts dictionary of schema models
   # (key is model name and value is schema as json-schema.org).

   models_as_jsonschema = {
       'articles': {'properties': {
           'title': {'type': 'string'},
           'author': {'relation': 'to-one', 'resource': ['people']},
           'comments': {'relation': 'to-many', 'resource': ['comments']},
       }},
       'people': {'properties': {
           'first-name': {'type': 'string'},
           'last-name': {'type': 'string'},
           'twitter': {'type': ['null', 'string']},
       }},
       'comments': {'properties': {
           'body': {'type': 'string'},
        'author': {'relation': 'to-one', 'resource': ['people']}
    }}
   }
   # If you type schema by hand, it could be more convenient to type it as yml in a file
   # instead

   s = Session('http://localhost:8080/', schema=models_as_jsonschema)
   a = s.create('articles') # Creates empty ResourceObject of 'articles' type
   a.title = 'Test title'

   # Validates and performs POST request, and finally updates resource based on server response
   a.commit(meta={'some_meta': 'data'})
   # Or with AsyncIO, remember to await
   await a.commit(meta={'some_meta': 'data'})

   # Commit metadata could be also saved in advance:
   a.commit_metadata = {'some_meta': 'data'}
   # You can also commit all changed resources in session by
   s.commit()
   # or with AsyncIO
   await s.commit()

   # Another example of resource creation, setting attributes and relationships & committing:
   # If you have underscores in your field names, you can pass them in fields keyword argument as
   # a dictionary:
   cust1 = s.create_and_commit('articles',
                               attribute='1',
                               dict_object__attribute='2',
                               to_one_relationship='3',
                               to_many_relationship=['1', '2'],
                               fields={'some_field_with_underscore': '1'}
                               )

   # Async:
   cust1 = await s.create_and_commit('articles',
                                     attribute='1',
                                     dict_object__attribute='2',
                                     to_one_relationship='3',
                                     to_many_relationship=['1', '2'],
                                     fields={'some_field_with_underscore': '1'}
                                     )

Deleting resources
------------------

.. code-block:: python

    # Delete resource
    cust1.delete() # Mark to be deleted
    cust1.commit() # Actually delete


Credits
=======

- Work was supported by Qvantel (http://qvantel.com).
- Author and package maintainer: Tuomas Airaksinen (https://github.com/tuomas2/).


License
=======

Copyright (c) 2017, Qvantel

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 - Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
 - Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
 - Neither the name of the Qvantel nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL QVANTEL BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

