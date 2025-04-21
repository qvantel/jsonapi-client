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

from typing import TYPE_CHECKING, Union, Dict, Sequence, Tuple
from enum import Enum

class FilterOperator(Enum):
    EQ = "EQ" # case insensitive - default if omitted
    NOT_EQ = "not_eq" # case insensitive
    EQL = "eql" # case sensitive 
    NOT_EQL = "not_eql" # case sensitive
    PREFIX = "prefix"
    NOT_PREFIX = "not_prefix"
    SUFFIX = "suffix"
    NOT_SUFFIX = "not_suffix"
    MATCH = "match"
    NOT_MATCH = "not_match"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"

EQ = FilterOperator.EQ
NOT_EQ = FilterOperator.NOT_EQ
EQL = FilterOperator.EQL
NOT_EQL = FilterOperator.NOT_EQL
PREFIX = FilterOperator.PREFIX
NOT_PREFIX = FilterOperator.NOT_PREFIX
SUFFIX = FilterOperator.SUFFIX
NOT_SUFFIX = FilterOperator.NOT_SUFFIX
MATCH = FilterOperator.MATCH
NOT_MATCH = FilterOperator.NOT_MATCH
GT = FilterOperator.GT
GTE = FilterOperator.GTE
LT = FilterOperator.LT
LTE = FilterOperator.LTE

EXISTS = (NOT_EQ, None)
NOT_EXISTS = (EQ, None)


if TYPE_CHECKING:
    FilterKeywords = Dict[str, Union[str, None, Sequence[Union[None, str, int, float, Tuple[FilterOperator, Union[None, str, int, float]]]]]]
    IncludeKeywords = Sequence[str]
    FieldKeywords  = Dict[str, Sequence[str]]



class Modifier:
    """
    Base class for query modifiers.
    You can derive your own class and use it if you have custom syntax.
    """
    def __init__(self, query_str: str='') -> None:
        self._query_str = query_str

    def url_with_modifiers(self, base_url: str) -> str:
        """
        Returns url with modifiers appended.

        Example:
            Modifier('filter[attr1]=1,2&filter[attr2]=2').filtered_url('doc')
              -> 'GET doc?filter[attr1]=1,2&filter[attr2]=2'
        """
        filter_query = self.appended_query()
        fetch_url = f'{base_url}?{filter_query}'
        return fetch_url

    def appended_query(self) -> str:
        return self._query_str

    def __add__(self, other: 'Modifier') -> 'Modifier':
        mods = []
        for m in [self, other]:
            if isinstance(m, ModifierSum):
                mods += m.modifiers
            else:
                mods.append(m)
        return ModifierSum(mods)


class ModifierSum(Modifier):
    def __init__(self, modifiers):
        self.modifiers = modifiers

    def appended_query(self) -> str:
        return '&'.join(m.appended_query() for m in self.modifiers)


class Filter(Modifier):
    """
    Implements query filtering for Session.get etc.
    You can derive your own filter class and use it if you have a
    custom filter query syntax.
    """
    def __init__(self, query_str: str='', **filter_kwargs: 'FilterKeywords') -> None:
        """
        :param query_str: Specify query string manually.
        :param filter_kwargs: Specify required conditions on result.
            Example: Filter(attribute='1', relation__attribute='2')
        """
        super().__init__(query_str)
        self._filter_kwargs = filter_kwargs

    # This and next method prevent any existing subclasses from breaking
    def url_with_modifiers(self, base_url: str) -> str:
        return self.filtered_url(base_url)

    def filtered_url(self, base_url: str) -> str:
        return super().url_with_modifiers(base_url)

    def appended_query(self) -> str:
        return super().appended_query() or self.format_filter_query(**self._filter_kwargs)

    def format_filter_query(self, **kwargs: 'FilterKeywords') -> str:
        """
        Filter class that implements url filtering scheme according to JSONAPI
        recommendations (http://jsonapi.org/recommendations/)
        """
        return '&'.join(f'filter[{key}]={value}'
                        for key, value in kwargs.items())

    def format_filter_query(self, **kwargs: 'FilterKeywords') -> str:
        """
        Filter class that implements URL filtering scheme according to JSONAPI
        recommendations (http://jsonapi.org/recommendations/).

        Supports additional operators like `eql`, `prefix`, `suffix`, and `match`.
        """
        filters = []
        for key, value in kwargs.items():
            key_parts = key.replace('.', '__').split('__')
            formatted_key = ''.join(f'[{part}]' for part in key_parts)
            operator = ''
            if isinstance(value, tuple) and len(value) == 2:
                op, value = value
                if op != EQ:
                    operator = f'[{op.value}]'
            if value is None: 
                value = 'null'
            filters.append(f'filter{formatted_key}{operator}={value}')
        return '&'.join(filters)

class Inclusion(Modifier):
    """
    Implements query inclusion for Session.get etc.
    """
    def __init__(self, *include_args: 'IncludeKeywords') -> None:
        super().__init__()
        self._include_args = include_args

    def appended_query(self) -> str:
        includes = ','.join(self._include_args)
        return f'include={includes}'

class BaseFields(Modifier):
    """
    Base class for implementing fields attributes.
    """
    def __init__(self, fields_args: 'FieldKeywords', query_key: str) -> None:
        super().__init__()
        self._fields_args = fields_args
        self._query_key = query_key

    def appended_query(self) -> str:
        return super().appended_query() or self.format_fields_query(**self._fields_args)

    def format_fields_query(self, **kwargs: 'FieldKeywords') -> str:
        return '&'.join(f'{self._query_key}[{resourceType}]={",".join(fields)}'
                        for resourceType, fields in kwargs.items())


class Fields(BaseFields):
    """
    Implements fields attributes.
    """
    def __init__(self, fields_args: 'FieldKeywords') -> None:
        super().__init__(fields_args, query_key='fields')


class ExtraFields(BaseFields):
    """
    Implements extra_fields attributes.
    """
    def __init__(self, fields_args: 'FieldKeywords') -> None:
        super().__init__(fields_args, query_key='extra_fields')
