#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

from zope import component

from zc.displayname.interfaces import IDisplayNameGenerator

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.app.testing.application_webtest import ApplicationLayerTest

class TestDisplayNameGenerators(ApplicationLayerTest):

	def test_note(self):
		from nti.dataserver.contenttypes import Note
		note = Note()
		note.title = IPlainTextContentFragment('the title')
		gen = component.getMultiAdapter((note, self.request), IDisplayNameGenerator)

		assert_that( gen(),
					 is_(note.title) )

		# no title, no body, a bad name
		note.title = IPlainTextContentFragment('')
		note.__name__ = 'tag:nextthought.com,2011-10:kaleywhite2-OID-0x0b12e1:55736572735f315f50726f64:uPZsT99MW1'
		assert_that( gen(), is_(''))

		# No title, but a body
		note.body = ('this is the body content, it is longer than it needs to be to get truncated',)
		assert_that( gen(), is_('this is the body content, i...'))
