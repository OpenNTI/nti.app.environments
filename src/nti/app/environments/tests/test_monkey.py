#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import fudge

from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import instance_of

import unittest

from sqlalchemy import create_engine

try:
	from .._monkey import geventPostgresclient_dialect
except ImportError:
    pass

class TestPatchSqlalchemy(unittest.TestCase):

    def test_postres_engine(self):
        from .._monkey import patch
        patch()
        engine = create_engine('gevent+postgres:///testdb.db')
        assert_that(engine, not_none())
        assert_that(engine.dialect, instance_of(geventPostgresclient_dialect))

    @fudge.patch('psycopg2.connect')
    def test_connect_uses_relstorage(self, pconn):
        from .._monkey import patch
        patch()
        engine = create_engine('gevent+postgres:///testdb.db')

        class StopExecution(Exception):
            pass

        # Make sure connect get gets called with the right connection_factory
        # Make calling it raise to stop all the crazy first connection initialization that sqlalchemy does
        # no luck trying to mock all the necessary things
        pconn.expects_call().with_args(database='testdb.db', connection_factory=engine.dialect._conn_class).raises(StopExecution)

        try:
            engine.connect()
        except StopExecution:
            pass
