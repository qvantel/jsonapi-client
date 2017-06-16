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

import logging
from itertools import chain
from typing import Optional, Union, Awaitable, TYPE_CHECKING
from urllib.parse import urlparse

from .common import AbstractJsonObject, jsonify_attribute_name, ResourceTuple
from .resourceobject import ResourceObject

if TYPE_CHECKING:
    from .document import Document

logger = logging.getLogger(__name__)


class Meta(AbstractJsonObject):
    """
    Object type for meta data

    http://jsonapi.org/format/#document-meta
    """
    def _handle_data(self, data):
        self.meta = data

    def __getattr__(self, name):
        return self.meta.get(jsonify_attribute_name(name))

    def __str__(self):
        return str(self.meta)


class Link(AbstractJsonObject):
    """
    Object type for a single link

    http://jsonapi.org/format/#document-links
    """
    def _handle_data(self, data):
        if data:
            if isinstance(data, str):
                self.href = data
            else:
                self.href = data['href']
                self.meta = Meta(self.session, data.get('meta', {}))
        else:
            self.href = ''

    def __eq__(self, other):
        return self.href == other.href

    def __bool__(self):
        return bool(self.href)

    @property
    def url(self) -> str:
        if urlparse(self.href).scheme:  # if href contains only relative link
            return self.href
        else:
            return f'{self.session.server_url}{self.href}'

    def __str__(self):
        return self.url if self.href else ''

    def fetch_sync(self) -> 'Optional[Document]':
        self.session.assert_sync()
        if self:
            return self.session.fetch_document_by_url(self.url)

    def fetch(self):
        if self.session.enable_async:
            return self.fetch_async()
        else:
            return self.fetch_sync()

    async def fetch_async(self) -> 'Optional[Document]':
        self.session.assert_async()
        if self:
            return await self.session.fetch_document_by_url_async(self.url)


class Links(AbstractJsonObject):
    """
    Object type for container of links

    http://jsonapi.org/format/#document-links
    """
    def _handle_data(self, data):
        self._links = {key: Link(self.session, value) for key, value in data.items()}

    def __getattr__(self, item):
        attr = self._links.get(item)
        if not attr:
            return Link(self.session, '')
        return attr

    def __bool__(self):
        return bool(self._links)

    def __dir__(self):
        return chain(super().__dir__(), self._links.keys())

    def __str__(self):
        return str(self._links)


class ResourceIdentifier(AbstractJsonObject):
    """
    Object type for resource identifier

    http://jsonapi.org/format/#document-resource-identifier-objects
    """
    def _handle_data(self, data):
        self.id:str = data.get('id')
        self.type:str = data.get('type')

    @property
    def url(self):
        return f'{self.session.url_prefix}/{self.type}/{self.id}'

    def __str__(self):
        return f'{self.type}: {self.id}'

    def fetch_sync(self, cache_only=True) -> 'ResourceObject':
        return self.session.fetch_resource_by_resource_identifier(self, cache_only)

    async def fetch_async(self, cache_only=True) -> 'ResourceObject':
        return await self.session.fetch_resource_by_resource_identifier_async(self,
                                                                              cache_only)

    def fetch(self, cache_only=True) \
            -> 'Union[Awaitable[ResourceObject], ResourceObject]':
        if self.session.enable_async:
            return self.fetch_async(cache_only)
        else:
            return self.fetch_sync(cache_only)

    def as_resource_identifier_dict(self) -> dict:
        return {'id': self.id, 'type': self.type} if self.id else None

    def __bool__(self):
        return self.id is not None

RESOURCE_TYPES = (ResourceObject, ResourceIdentifier, ResourceTuple)
ResourceTypes = Union[ResourceObject, ResourceIdentifier, ResourceTuple]
