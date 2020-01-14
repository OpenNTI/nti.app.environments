#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import starts_with
from hamcrest import is_

from pyramid.renderers import render
from pyramid.renderers import render_to_response

from nti.app.testing.application_webtest import ApplicationLayerTest

class TestPDFRender(ApplicationLayerTest):
	
	no_cache = False

	def test_render(self):
		# Fix up the dummy request
		self.request.pragma = None
		self.request.cache_control = self
		self.request.accept_encoding = None
		self.request.if_none_match = False
		result = render( "test_pdf_template.rml",
						 {'username': 'foo@bar', 'realname': 'Snoop Dogg', 'email': 'foo@bar'},
						 request=self.request )

		assert_that( result, starts_with(b'%PDF-1.4'))
		del self.request.cache_control # break cycle

	def test_content_disposition(self):
		# Fix up the dummy request
		self.request.pragma = None
		self.request.cache_control = self
		self.request.accept_encoding = None
		self.request.if_none_match = False

		# content_disposition is already set, ignore filename
		self.request.response.content_disposition = 'attachment; filename="old.pdf"'
		self.request.filename = "abc.pdf"

		result = render_to_response("test_pdf_template.rml",
									{'username': 'foo@bar', 'realname': 'Snoop Dogg', 'email': 'foo@bar'},
									request=self.request,
									response=self.request.response)

		assert_that(self.request.response.content_disposition, is_('attachment; filename="old.pdf"'))

		# content_disposition is not set, and existing filename
		self.request.response.content_disposition = None
		self.request.filename = "abc.pdf"

		result = render_to_response("test_pdf_template.rml",
									{'username': 'foo@bar', 'realname': 'Snoop Dogg', 'email': 'foo@bar'},
									request=self.request,
									response=self.request.response)
		assert_that(self.request.response.content_disposition, is_('filename="abc.pdf"'))

		# content_disposition is not set and filename doesn't exist
		self.request.response.content_disposition = None
		self.request.filename = None

		result = render_to_response("test_pdf_template.rml",
									{'username': 'foo@bar', 'realname': 'Snoop Dogg', 'email': 'foo@bar'},
									request=self.request,
									response=self.request.response)
		assert_that(self.request.response.content_disposition, is_(None))

		del self.request.cache_control # break cycle
