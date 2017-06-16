CHANGELOG
=========

[2017-03-23] 0.9.1
 - Fix async content_type checking
 - Use Python 3's new typing.NamedTuple instead of collections.NamedTuple
 - Make included resources available from Document
 - ResourceObject.json property

[2017-04-03] 0.9.2
 - Github release.

[2017-04-03] 0.9.3
 - Added aiohttp to install requirements

[2017-xx-xx] 0.9.4
 - AsyncIO support for context manager usage of Session

0.9.4 (2017-06-16)
 - Remove ? from filenames (illegal in Windows)
 - Pass event loop aiohttp's ClientSession
 - Return resource from .commit if return status is 202
 - Support underscores in field names in Session.create() through fields keyword argument.
 - Add support for extra arguments such as authentication object

