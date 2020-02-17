#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

import os

from pyramid.testing import setUp as psetUp
from pyramid.testing import tearDown as ptearDown

import zope

from zope import component

from zope.component.hooks import setHooks

from nti.testing.layers import ConfiguringLayerMixin

from nti.app.environments.interfaces import IOnboardingSettings

from nti.environments.management.config import configure_settings

from nti.environments.management.interfaces import ISettings

from nti.environments.management import tests

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


class RenderTestLayer(ConfiguringLayerMixin):
	set_up_packages = ('nti.app.environments',)

	request = None

	@classmethod
	def setUp(cls):
		settings = {
			'hubspot_api_key': 'zzz',
			'hubspot_portal_id': 'kkk',
			'nti.environments.management.config': os.path.join(os.path.dirname(tests.__file__), 'test.ini')
		}
		component.getGlobalSiteManager().registerUtility(settings, IOnboardingSettings)

		cls.__env_config = configure_settings(settings)
		cls.setUpPackages()
		cls.config = psetUp(registry=component.getGlobalSiteManager(), request=cls.request, hook_zca=False)
		cls.config.setup_registry()
		cls.config.add_renderer(name='rest', factory='nti.app.environments.renderers.renderers.DefaultRenderer')
		cls.config.add_renderer(name='.rml', factory="nti.app.environments.renderers.pdf.PDFRendererFactory")

	@classmethod
	def tearDown(cls):
		ptearDown()
		cls.tearDownPackages()
		component.getGlobalSiteManager().unregisterUtility(cls.__env_config, ISettings)
		zope.testing.cleanup.cleanUp()
		setHooks()  # but these must be back!
	

	@classmethod
	def testSetUp(cls, test=None):
		pass
        
	@classmethod
	def testTearDown(cls):
	        pass
