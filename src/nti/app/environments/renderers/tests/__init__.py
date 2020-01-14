#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

import zope

from zope import component

from zope.component.hooks import setHooks

from nti.testing.layers import ConfiguringLayerMixin

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class RenderTestLayer(ConfiguringLayerMixin):
	set_up_packages = ('nti.app.environments',)

	request = None

	@classmethod
	def setUp(cls):
		cls.setUpPackages()
		cls.config = psetUp(registry=component.getGlobalSiteManager(), request=cls.request, hook_zca=False)
		cls.config.setup_registry()
		cls.config.add_renderer(name='rest', factory='nti.app.environments.renderers.renderers.DefaultRenderer')
		cls.config.add_renderer(name='.rml', factory="nti.app.environments.renderers.pdf.PDFRendererFactory")

	@classmethod
	def tearDown(cls):
		ptearDown()
		cls.tearDownPackages()
		zope.testing.cleanup.cleanUp()
		setHooks()  # but these must be back!
	

	@classmethod
	def testSetUp(cls, test=None):
		pass
        
	@classmethod
	def testTearDown(cls):
	        pass
