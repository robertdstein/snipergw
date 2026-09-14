"""
Test package init.

Importing snipergw.submit.winter (transitively pulled in by several test
modules below, e.g. via snipergw.submit/__init__.py or snipergw.run)
constructs a module-level WinterAPI() singleton at import time. Its
__init__ calls WinterAPI.check_version(), which makes an unguarded
network call to winter.caltech.edu with no exception handling -- unlike
WinterAPI.ping() (also called from __init__), which already catches
connection errors. That unguarded call has caused CI runs to fail with a
connection timeout, which has nothing to do with the tests actually
being run.

Patch both network-calling staticmethods to no-ops here, before any test
module gets imported, so constructing WinterAPI() never depends on
network access during test collection or runs.
"""

from winterapi.messenger import WinterAPI

WinterAPI.ping = staticmethod(lambda: True)
WinterAPI.check_version = staticmethod(lambda: None)
