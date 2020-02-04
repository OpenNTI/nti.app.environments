#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
When RelStorage is installed with psycopg2 and gevent a global wait callback is installed.
That wait callback expects the Relstorage custom connection which creates issues
when trying to use psycopg2 with sqlalchmey.

Install a custom dialect that uses the RelStorage connection for sqlalchemy.
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

logger = __import__('logging').getLogger(__name__)

try:
    from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
    from relstorage.adapters.postgresql.drivers.psycopg2 import GeventPsycopg2Driver
    import psycopg2
except ImportError:
    pass
else:
    class geventPostgresclient_dialect(PGDialect_psycopg2):
        driver = "gevent+postgres"

        def __init__(self, *args, **kwargs):
            super(geventPostgresclient_dialect, self).__init__(*args, **kwargs)
            self._conn_class = GeventPsycopg2Driver().connect

        def connect(self, *args, **kwargs):
            kwargs['connection_factory'] = self._conn_class
            return psycopg2.connect(*args, **kwargs)

    from sqlalchemy.dialects import registry
    registry.register("gevent.postgres", __name__, "geventPostgresclient_dialect")

def patch():
    pass
