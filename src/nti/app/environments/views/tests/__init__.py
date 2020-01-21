import functools
import unittest
import transaction

from contextlib import contextmanager

from zope import component
from zope.testing.cleanup import cleanUp

from pyramid import testing
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.interfaces import IRootFactory

from webtest import TestApp

from nti.app.environments import main
from nti.app.environments.configure import root_factory

from nti.app.environments.models.interfaces import IOnboardingRoot


class BaseAppTest(unittest.TestCase):

    testapp = None
    request = None

    def setUp(self):
        self.request = testing.DummyRequest()
        self.request._set_registry(component.getGlobalSiteManager())
        self.settings={
            'zodbconn.uri' : 'memory://',
            'google_client_id': 'xxx',
            'google_client_secret': 'yyy',
            'hubspot_api_key': 'zzz',
            'hubspot_portal_id': 'kkk',
            'new_site_request_notification_email': 'test@example.com',
            'celery.broker_url': 'memory',
            'celery.backend_url': 'memory'
        }

    def tearDown(self):
        cleanUp()
        transaction.abort()

    def _make_environ(self, username=None):
        result = { 'REMOTE_USER': username } if username else {}
        return result

    def _root(self, request=None):
        return IOnboardingRoot(request or self.request)


class DummyCookieHelper(object):

    def __init__(self, result):
        self.result = result

    def identify(self, request):
        return {'userid': request.environ.get('REMOTE_USER')}

    def remember(self, request, userid, **kw):
        return []

    def forget(self, request):
        return []


def dummy_callback(userid='admin001', request=None):
    if userid == 'admin001':
        return ['role:nti.roles.admin']
    elif userid=='user001':
        return ['user001']


def with_test_app(auth_cookie=True, callback=dummy_callback):
    def decorator(func):
        @functools.wraps(func)
        def func_wrapper(self):
            with ensure_free_txn():
                settings = self.settings
                app = main({}, **settings)
                authn_policy = app.registry.getUtility(IAuthenticationPolicy)
                if auth_cookie:
                    authn_policy.cookie = DummyCookieHelper({})
                if callback:
                    authn_policy.callback = callback

                assert component.getSiteManager() is app.registry
                self.testapp = TestApp(app)
            func(self)
        return func_wrapper
    return decorator


@contextmanager
def ensure_free_txn():
    # transaction in transaction_tween_factory are explicit, so before call testapp.
    # it needs to make sure no existing transaction exists.
    manager = transaction.manager.manager
    yield
    if manager._txn is not None:
        if not manager.isDoomed():
            manager.commit()
        else:
            manager.abort()

        manager.free(manager._txn)
