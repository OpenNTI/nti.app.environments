#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from ZODB.broken import Broken

from pyramid.request import Request

from nti.app.renderers.rest import find_content_type

from nti.externalization.externalization import toExternalObject

from nti.app.testing.layers import NewRequestLayerTest

class TestContentType(NewRequestLayerTest):
	
	mimeType= 'application/vnd.nextthought.testcontenttype'
	
	def beginRequest( self, request_factory=Request.blank, request_args=('/') ):
		return super(TestContentType,self).beginRequest(request_factory, request_args)

	def test_no_accept_no_param(self):

		assert_that( find_content_type( self.request ),
					 is_( 'application/vnd.nextthought+json' ) )

	def test_generic_accept_not_overriden_by_query(self):
		self.request = Request.blank( '/?format=plist' )
		self.request.accept = '*/*'
		assert_that( find_content_type( self.request ),
					 is_( 'application/vnd.nextthought+json' ) )

	def test_xml_types_are_json( self ):
		self.request.accept = 'application/xml'

		assert_that( find_content_type( self.request, data={} ),
					 is_( 'application/vnd.nextthought+json' ) )

		self.request.accept = 'application/vnd.nextthought+json'

		assert_that( find_content_type( self.request, data={} ),
					 is_( 'application/vnd.nextthought+json' ) )

	def test_nti_type( self ):
		self.request.accept = 'application/json'

		assert_that( find_content_type( self.request, data=self ),
					 is_( 'application/vnd.nextthought.testcontenttype+json' ) )

		self.request.accept = None

		assert_that( find_content_type( self.request, data=self ),
					 is_( 'application/vnd.nextthought.testcontenttype+json' ) )

class TestRender(NewRequestLayerTest):

	def test_broken(self):
		assert_that( toExternalObject( Broken() ),
					 is_( {"Class": "BrokenObject"} ) )

		assert_that( toExternalObject( [Broken()] ),
					 is_( [{ "Class": "BrokenObject"}] ) )
