from hamcrest import assert_that
from hamcrest import is_

from pyramid.interfaces import IRequest

from zope.publisher.interfaces import ISkinType

import fudge

import unittest

from zope import component
from zope import interface

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn

from nti.app.environments.models.interfaces import ILMSSitesContainer

from nti.app.environments.views.interfaces import IEndUserBrowserRequest

class TestErrorViews(BaseAppTest):

    @with_test_app()
    def test_authenticated_forbidden_403(self):
        self.testapp.get('/onboarding/sites/@@list',
                         status=403,
                         extra_environ=self._make_environ(username='user001'))

    @with_test_app()
    def test_unauthenticated_xhr_401(self):
        self.testapp.get('/onboarding/sites/@@list',
                         xhr=True,
                         status=401,
                         extra_environ=self._make_environ(username=None))
        
    @with_test_app()
    def test_unauthenticated_browser_redirect(self):
        resp = self.testapp.get('/onboarding/sites/@@list',
                         status=302,
                         extra_environ=self._make_environ(username=None))
        assert_that(resp.location, is_('http://localhost/login?success=%2Fonboarding%2Fsites%2F%40%40list'))

    @with_test_app()
    def test_unauthenticated_enduser_redirect(self):
        gsm = component.getGlobalSiteManager()
        
        gsm.registerAdapter(IEndUserBrowserRequest, (ILMSSitesContainer, IRequest,), ISkinType)
        resp = self.testapp.get('/onboarding/sites/@@list',
                                status=302,
                                extra_environ=self._make_environ(username=None))
            
        assert_that(resp.location, is_('http://localhost/email-auth?return=%2Fonboarding%2Fsites%2F%40%40list'))
