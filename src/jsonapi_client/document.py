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
from typing import TYPE_CHECKING, Iterator, AsyncIterator, List

from .common import AbstractJsonObject
from .exceptions import ValidationError, DocumentError
from .objects import Meta, Links
from .resourceobject import ResourceObject

if TYPE_CHECKING:
    from .session import Session


logger = logging.getLogger(__name__)


class Document(AbstractJsonObject):
    """
    Top level of JSON API document.
    Contains one or more ResourceObjects.

    http://jsonapi.org/format/#document-top-level
    """

    #: List of ResourceObjects contained in this Document
    resources: List['ResourceObject']

    def __init__(self, session: 'Session',
                 json_data: dict,
                 url: str,
                 no_cache: bool=False) -> None:
        self._no_cache = no_cache  # if true, do not store resources to session cache
        self._url = url
        super().__init__(session, json_data)

    @property
    def url(self) -> str:
        return self._url

    @property
    def resource(self) -> 'ResourceObject':
        """
        If there is only 1 ResourceObject contained in this Document, return it.
        """
        if len(self.resources) > 1:
            logger.warning('There are more than 1 item in document %s, please use '
                           '.resources!', self)
        return self.resources[0]

    def _handle_data(self, json_data):
        data = json_data.get('data')

        self.resources = []

        if data:
            if isinstance(data, list):
                self.resources.extend([ResourceObject(self.session, i) for i in data])
            elif isinstance(data, dict):
                self.resources.append(ResourceObject(self.session, data))

        self.errors = json_data.get('errors')
        if [data, self.errors] == [None]*2:
            raise ValidationError('Data or errors is needed')
        if data and self.errors:
            logger.error('Data and errors can not both exist in the same document')

        self.meta = Meta(self.session, json_data.get('meta', {}))

        self.jsonapi = json_data.get('jsonapi', {})
        self.links = Links(self.session, json_data.get('links', {}))
        if self.errors:
            raise DocumentError(f'Error document was fetched. Details: {self.errors}',
                                errors=self.errors)
        self.included = [ResourceObject(self.session, i)
                         for i in json_data.get('included', [])]
        if not self._no_cache:
            self.session.add_resources(*self.resources, *self.included)

    def __str__(self):
        return f'{self.resources}' if self.resources else f'{self.errors}'

    def _iterator_sync(self) -> 'Iterator[ResourceObject]':
        yield from self.resources
        if self.links.next:
            next_doc = self.links.next.fetch()
            yield from next_doc.iterator()

    async def _iterator_async(self) -> 'AsyncIterator[ResourceObject]':
        for res in self.resources:
            yield res

        if self.links.next:
            next_doc = await self.links.next.fetch()
            async for res in next_doc.iterator():
                yield res

    def iterator(self):
        """
        Iterate through all resources of this Document and follow pagination until
        there's no more resources.

        If Session is in async mode, this needs to be used with async for.
        """
        if self.session.enable_async:
            return self._iterator_async()
        else:
            return self._iterator_sync()

    def mark_invalid(self):
        """
        Mark this Document and it's resources invalid.
        """
        super().mark_invalid()
        for r in self.resources:
            r.mark_invalid()