import os
import functools
import unittest
import transaction

from contextlib import contextmanager

from zope import component
from zope.testing.cleanup import cleanUp

from perfmetrics import statsd_client_stack

from pyramid import testing
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.interfaces import IRootFactory

from webtest import TestApp

from nti.app.environments import main
from nti.app.environments.configure import root_factory

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.environments.management import tests

from nti.fakestatsd import FakeStatsDClient


class BaseAppTest(unittest.TestCase):

    testapp = None
    app = None
    request = None

    def setUp(self):
        self.request = testing.DummyRequest()
        self.request._set_registry(component.getGlobalSiteManager())

        self.settings={
            'zodbconn.uri' : 'memory://',
            'google_client_id': 'xxx',
            'google_client_secret': 'yyy',
            'new_site_request_notification_email': 'test@example.com',
            'site_setup_failure_notification_email': 'test@example.com',
            'nti.environments.management.config': os.path.join(os.path.dirname(tests.__file__), 'test.ini'),
            'zcml.features': 'devmode'
        }
        self.statsd = FakeStatsDClient()
        statsd_client_stack.push(self.statsd)

    def tearDown(self):
        cleanUp()
        transaction.abort()
        statsd_client_stack.pop()

    def _make_environ(self, username=None):
        result = { 'REMOTE_USER': username } if username else {}
        return result

    def _root(self, request=None):
        return IOnboardingRoot(request or self.request)

    def sent_stats(self):
        """
        Returns a tuple of gauge and counters that were sent
        """
        guages = {}
        counters = {}
        for metric in self.statsd:
            if metric.kind == 'g':
                guages[metric.name] = metric.value
            elif metric.kind == 'c':
                counters[metric.name] = int(metric.value)
        return guages, counters


class DummyCookieHelper(object):

    def __init__(self, result):
        self.result = result

    def identify(self, request):
        return {'userid': request.environ.get('REMOTE_USER')}

    def remember(self, request, userid, **kw):
        return []

    def forget(self, request):
        return []

TEST_USERS = {
    'admin001': ['role:nti.roles.admin'],
    'manager001': ['role:nti.roles.account-management'],
    'ops001': ['role:nti.roles.ops-management'],
    'user001': [],
    'user001@example.com': [],
    'user002@example.com': []
}

def dummy_callback(userid='admin001', request=None):
    if userid not in TEST_USERS:
        return [userid]
    
    groups = [userid]
    groups.extend(TEST_USERS[userid])
    return groups


def with_test_app(auth_cookie=True, callback=dummy_callback):
    def decorator(func):
        @functools.wraps(func)
        def func_wrapper(self):
            with ensure_free_txn():
                settings = self.settings
                if self.app is None:
                    self.app = main({}, **settings)
                    authn_policy = self.app.registry.getUtility(IAuthenticationPolicy)
                    if auth_cookie:
                        authn_policy.policies['auth_tkt'].cookie = DummyCookieHelper({})
                    if callback:
                        # TODO this doesn't look right to me, we are completely
                        # bypassing the callback configured in the actual policy,
                        # which could be non-trival.
                        authn_policy.policies['auth_tkt'].callback = callback

                assert component.getSiteManager() is self.app.registry
                self.testapp = TestApp(self.app)
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
