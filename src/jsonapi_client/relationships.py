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

import collections
import logging
from typing import List, Union, Iterable, Dict, Tuple, Awaitable, TYPE_CHECKING

from .common import AbstractJsonObject, RelationType, ResourceTuple
from .objects import (Meta, Links, ResourceIdentifier, RESOURCE_TYPES)
from .resourceobject import ResourceObject

logger = logging.getLogger(__name__)

R_IDENT_TYPES = Union[str, ResourceObject, ResourceIdentifier, ResourceTuple]

if TYPE_CHECKING:
    from .filter import Filter
    from .document import Document
    from .session import Session


class AbstractRelationship(AbstractJsonObject):
    """
    Relationships are containers for ResourceObjects related to relationships.
    ResourceObjects are automatically fetched if not in async mode.
    If in async mode, .fetch() needs to be awaited first.

    http://jsonapi.org/format/#document-resource-object-relationships
    """

    def __init__(self,
                 session: 'Session',
                 data: dict,
                 resource_types: List[str]=None,
                 relation_type: str='') -> None:
        """
        :param resource_types: List of allowed resource types
        :param relation_type: Relation type, either 'to-one' or 'to-many',
            or not specified (empty string).
        """
        self._resources: Dict[Tuple[str, str], ResourceObject] = None
        self._invalid = False
        self._is_dirty: bool = False
        self._resource_types = resource_types or []
        self._relation_type = relation_type

        super().__init__(session, data)

    @property
    def is_single(self) -> bool:
        raise NotImplementedError

    def _filter_sync(self, filter: 'Filter') -> 'Document':
        url = filter.filtered_url(self.url)
        return self.session.fetch_document_by_url(url)

    async def _filter_async(self, filter_obj: 'Filter'):
        url = filter_obj.filtered_url(self.url)
        return self.session.fetch_document_by_url_async(url)

    def filter(self, filter: 'Filter') -> 'Union[Awaitable[Document], Document]':
        """
        Receive filtered list of resources. Use Filter instance.

        If in async mode, this needs to be awaited.
        """
        if self.session.enable_async:
            return self._filter_async(filter)
        else:
            return self._filter_sync(filter)

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    def mark_clean(self):
        """
        Mark this relationship as clean (not modified/dirty).
        """
        self._is_dirty = False

    def mark_dirty(self):
        """
        Mark this relationship as modified/dirty.
        """
        self._is_dirty = True

    async def _fetch_async(self) -> 'List[ResourceObject]':
        raise NotImplementedError

    def _fetch_sync(self) -> 'List[ResourceObject]':
        raise NotImplementedError

    def fetch(self) -> 'Union[Awaitable[List[ResourceObject]], List[ResourceObject]]':
        """
        Fetch ResourceObjects. In practice this needs to be used only if in async mode
        and then this needs to be awaited.

        In blocking (sync) mode this is called automatically when .resource or
        .resources is accessed.
        """
        if self.session.enable_async:
            return self._fetch_async()
        else:
            return self._fetch_sync()

    def _handle_data(self, data):
        self.links = Links(self.session, data.get('links', {}))
        self.meta = Meta(self.session, data.get('meta', {}))
        self._resource_data = data.get('data', {})

    @property
    def resources(self) -> 'List[Union[ResourceIdentifier, ResourceObject]]':
        """
        Return related ResourceObjects. If this relationship has been
        modified (waiting to be committed (PATCH)), this also returns
        ResourceIdentifier objects of those new linked resources.

        In async mode, you need to first await .fetch()
        """
        return ((self._resources is not None and list(self._resources.values()))
                or self._fetch_sync())

    @property
    def resource(self) -> 'ResourceObject':
        """
        If there is only 1 resource, return it.

        In async mode, you need to first await .fetch()
        """
        if len(self.resources) > 1:
            logger.warning('More than 1 resource, use .resources instead!')
        return self.resources[0]

    @property
    def as_json_resource_identifiers(self) -> dict:
        """
        Return resource identifier -style linkage (used in posting/patching)

        i.e.

        {'type': 'model_name', 'id': '1'}

        or list of these.
        """
        raise NotImplementedError

    @property
    def is_fetched(self) -> bool:
        return bool(self._resources)

    def set(self, new_value, type_=None) -> None:
        """
        This function is used when new values is set as targets of this relationship.

        Implement in subclasses
        """
        raise NotImplementedError

    def __str__(self):
        raise NotImplementedError

    @property
    def url(self) -> str:
        raise NotImplementedError

    @property
    def type(self) -> str:
        """
        Return the type of this relationship, if there is only 1 allowed type.
        """
        if len(self._resource_types) != 1:
            raise TypeError('Type needs to be specified manually, use .set or .add')
        return self._resource_types[0]

    def __bool__(self):
        raise NotImplementedError

    def _value_to_identifier(self, value: R_IDENT_TYPES, type_: str='') \
            -> 'Union[ResourceIdentifier, ResourceObject]':
        if isinstance(value, RESOURCE_TYPES):
            r_ident = ResourceIdentifier(self.session, {'id': value.id, 'type': value.type})
        else:
            r_ident = ResourceIdentifier(self.session, {'id': value,
                                                     'type': type_ or self.type})
        res = self._resources and self._resources.get((r_ident.type, r_ident.id))
        return res or r_ident


class SingleRelationship(AbstractRelationship):
    """
    Relationship class for to-one type relationships, that are received from
    server as ResourceIdentifiers.
    """
    def _handle_data(self, data):
        super()._handle_data(data)
        self._resource_identifier = ResourceIdentifier(self.session, self._resource_data)
        del self._resource_data  # This is not intended to be used after this

    async def _fetch_async(self) -> 'List[ResourceObject]':
        self.session.assert_async()
        res_id = self._resource_identifier
        res = await self.session.fetch_resource_by_resource_identifier_async(res_id)
        self._resources = {(res.type, res.id): res}
        return list(self._resources.values())

    def _fetch_sync(self) -> 'List[ResourceObject]':
        self.session.assert_sync()
        res_id = self._resource_identifier
        res = self.session.fetch_resource_by_resource_identifier(res_id)
        self._resources = {(res.type, res.id): res}
        return list(self._resources.values())

    def __bool__(self):
        return bool(self._resource_identifier)

    def __str__(self):
        return str(self._resource_identifier)

    @property
    def is_single(self) -> bool:
        return True

    @property
    def url(self) -> str:
        return self._resource_identifier.url

    @property
    def as_json_resource_identifiers(self) -> dict:
        return self._resource_identifier.as_resource_identifier_dict()

    def set(self, new_value: R_IDENT_TYPES, type_: str='') -> None:

        self._resource_identifier = self._value_to_identifier(new_value, type_)
        self.mark_dirty()


class MultiRelationship(AbstractRelationship):
    """
    Relationship class for to-many type relationships, that are received from
    server as ResourceIdentifiers.
    """
    def _handle_data(self, data):
        super()._handle_data(data)
        self._resource_identifiers = [ResourceIdentifier(self.session, d)
                                      for d in self._resource_data]
        del self._resource_data

    @property
    def is_single(self) -> bool:
        return False

    async def _fetch_async(self) -> 'List[ResourceObject]':
        self.session.assert_async()
        self._resources = {}
        for res_id in self._resource_identifiers:
            res = await self.session.fetch_resource_by_resource_identifier_async(res_id)
            self._resources[(res.type, res.id)] = res
        return list(self._resources.values())

    def _fetch_sync(self) -> 'List[ResourceObject]':
        self.session.assert_sync()
        self._resources = {}
        for res_id in self._resource_identifiers:
            res = self.session.fetch_resource_by_resource_identifier(res_id)
            self._resources[(res.type, res.id)] = res
        return list(self._resources.values())

    def __str__(self):
        return str(self._resource_identifiers)

    @property
    def url(self) -> str:
        return self.links.related

    @property
    def as_json_resource_identifiers(self) -> List[dict]:
        return [res.as_resource_identifier_dict() for res in self._resource_identifiers]

    def set(self, new_values: Iterable[R_IDENT_TYPES], type_: str=None) -> None:
        self._resource_identifiers = [self._value_to_identifier(value, type_)
                                      for value in new_values]
        self.mark_dirty()

    def clear(self):
        """
        Remove all target resources (commit will remove them on server side).
        """
        self._resource_identifiers.clear()
        self.mark_dirty()

    def add(self, new_value: Union[R_IDENT_TYPES, Iterable[R_IDENT_TYPES]], type_=None) -> None:
        """
        Add new resources
        """
        if type_ is None:
            type_ = self.type
        if isinstance(new_value, collections.Iterable):
            self._resource_identifiers.extend(
                [self._value_to_identifier(val, type_) for val in new_value])
        else:
            self._resource_identifiers.append(self._value_to_identifier(new_value, type_))

        self.mark_dirty()

    def __add__(self, other):
        return self.add(other)

    def __bool__(self):
        return bool(self._resource_identifiers)


class LinkRelationship(AbstractRelationship):
    """
    Relationship class for to-one or to-many type relationships, that are received from
    server with only link information (no ResourceIdentifiers).
    """
    def __init__(self, *args, **kwargs):
        self._resource_identifiers = None
        self._document: 'Document' = None
        super().__init__(*args, **kwargs)

    def __bool__(self):
        return bool(self._resource_identifiers)

    @property
    def document(self) -> 'Document':
        doc = getattr(self, '_document', None)
        if doc is None:
            self._fetch_sync()
        return self._document

    @property
    def is_single(self) -> bool:
        if self._relation_type:
            return self._relation_type == RelationType.TO_ONE
        else:
            return False

    async def _fetch_async(self) -> 'List[ResourceObject]':
        self.session.assert_async()
        self._document = \
            await self.session.fetch_document_by_url_async(self.links.related.url)
        self._resources = {(r.type, r.id): r for r in self._document.resources}
        return list(self._resources.values())

    def _fetch_sync(self) -> 'List[ResourceObject]':
        self.session.assert_sync()
        self._document = self.session.fetch_document_by_url(self.links.related.url)
        self._resources = {(r.type, r.id): r for r in self._document.resources}
        return list(self._resources.values())

    def mark_clean(self):
        self._is_dirty = False
        if self._document:
            self._document.mark_invalid()

    def __str__(self):
        return (f'{self.url} ({len(self.resources)}) dirty: {self.is_dirty}'
                if self.is_fetched else self.url)

    @property
    def as_json_resource_identifiers(self) -> Union[list, dict]:
        if self.is_single:
            return self.resource.as_resource_identifier_dict()
        else:
            return [res.as_resource_identifier_dict() for res in self.resources]

    @property
    def url(self) -> str:
        return str(self.links.related)

    def set(self, new_value: Union[Iterable[R_IDENT_TYPES], R_IDENT_TYPES],
            type_: str='') -> None:
        if isinstance(new_value, collections.Iterable):
            if self.is_single:
                logger.warning('This should contain list of resources, '
                               'but only one is given')
            resources = [self._value_to_identifier(val, type_) for val in new_value]
            self._resources = {(r.type, r.id):r for r in resources}
        else:
            if not self.is_single:
                logger.warning('This should contain only 1 resource, '
                               'but a list of values is given')
            res = self._value_to_identifier(new_value, type_)
            self._resources = {(res.type, res.id): res}
        self.mark_dirty()


class MetaRelationship(AbstractRelationship):
    """
    Handle relationship manually through meta object. We don't know what to do
    about them as they are custom data.
    """

