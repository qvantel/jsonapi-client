"""
JSON API Python client 
https://github.com/qvantel/jsonapi-client

(see JSON API specification in http://jsonapi.org/)

Copyright (c) 2017, Qvantel
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the Qvantel nor the
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
"""

import asyncio
import logging
from typing import Union, TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from .session import Session

logger = logging.getLogger(__name__)


class HttpStatus:
    OK_200 = 200
    CREATED_201 = 201
    ACCEPTED_202 = 202
    NO_CONTENT_204 = 204
    FORBIDDEN_403 = 403
    NOT_FOUND_404 = 404
    CONFLICT_409 = 409

    HAS_RESOURCES = (OK_200, CREATED_201)
    ALL_OK = (OK_200, CREATED_201, ACCEPTED_202, NO_CONTENT_204)


class HttpMethod:
    POST = 'post'
    PATCH = 'patch'
    DELETE = 'delete'


class RelationType:
    TO_ONE = 'to-one'
    TO_MANY = 'to-many'


class AbstractJsonObject:
    """
    Base for all JSON API specific objects
    """
    def __init__(self, session: 'Session', data: Union[dict, list]) -> None:
        self._invalid = False
        self._session = session
        self._handle_data(data)

    @property
    def session(self):
        return self._session

    def _handle_data(self, data: Union[dict, list]) -> None:
        """
        Store data
        """
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__}: {str(self)} ({id(self)})>'

    def __str__(self):
        raise NotImplementedError

    @property
    def url(self) -> str:
        raise NotImplementedError

    def mark_invalid(self):
        self._invalid = True


def error_from_response(response):
    try:
        error_str = response.json()['errors'][0]['title']
    except Exception:
        error_str = '?'
    return error_str


def jsonify_attribute_name(name):
    return name.replace('__', '.').replace('_', '-')


def dejsonify_attribute_name(name):
    return name.replace('.', '__').replace('-', '_')


def jsonify_attribute_names(iterable):
    for i in iterable:
        yield jsonify_attribute_name(i)


def dejsonify_attribute_names(iterable):
    for i in iterable:
        yield dejsonify_attribute_name(i)


async def execute_async(func, *args):
    """Shortcut to asynchronize normal blocking function"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


class cached_property(object):
    """
    From Django code

    Decorator that converts a method with a single self argument into a
    property cached on the instance.

    Optional ``name`` argument allows you to make cached properties of other
    methods. (e.g.  url = cached_property(get_absolute_url, name='url') )
    """
    def __init__(self, func, name=None):
        self.func = func
        self.__doc__ = getattr(func, '__doc__')
        self.name = name or func.__name__

    def __get__(self, instance, type=None):
        if instance is None:
            return self
        res = instance.__dict__[self.name] = self.func(instance)
        return res


class AttributeProxy:
    """
    Attribute proxy used in ResourceObject.fields etc.
    """
    def __init__(self, target_object=None):
        self._target_object = target_object

    def __getitem__(self, item):
        return self._target_object[item]

    def __setitem__(self, key, value):
        self._target_object[key] = value

    def __getattr__(self, item):
        try:
            return self[jsonify_attribute_name(item)]
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        if key == '_target_object':
            return super().__setattr__(key, value)
        try:
            self[jsonify_attribute_name(key)] = value
        except KeyError:
            raise AttributeError


class ResourceTuple(NamedTuple):
    id: str
    type: str

