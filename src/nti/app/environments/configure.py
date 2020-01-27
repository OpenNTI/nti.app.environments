import re

import pyramid_zcml

from pyramid.authorization import ACLAuthorizationPolicy

from pyramid.config import Configurator

from pyramid.session import SignedCookieSessionFactory

from pyramid.tweens import EXCVIEW

from zope.component import getGlobalSiteManager

from nti.app.pyramid_zope.traversal import ZopeResourceTreeTraverser

from nti.environments.management.config import configure_settings

from .auth import AuthenticationPolicy

from .models.interfaces import IOnboardingRoot

from .settings import init_app_settings

def root_factory(request):
    return IOnboardingRoot(request).__parent__

# https://docs.pylonsproject.org/projects/venusian/en/latest/index.html#ignore-scan-argument
_ignore_tests_scan_callable = re.compile('tests$').search

def configure(settings=None, registry=None):
    # Use ZCA global site manager
    if registry is None:
        registry = getGlobalSiteManager()
    
    with Configurator(registry=registry) as config:
        config.setup_registry(settings=settings)

        # initialize global constants
        init_app_settings(settings)

        # initialize env mgmt settings
        configure_settings(settings)

        config.include(pyramid_zcml)
        config.include('pyramid_retry')
        config.include('pyramid_zodbconn')

        config.add_tween('nti.transactions.pyramid_tween.transaction_tween_factory',
                         over=EXCVIEW)

        config.set_root_factory(root_factory)
        config.include('pyramid_chameleon')
        config.include('pyramid_mako')
        config.include('.routes')
        config.load_zcml('configure.zcml')

        # Load celery
        config.include('.tasks')
        
        # security policies
        authn_policy = AuthenticationPolicy('foo',
                                            hashalg='sha512')
        authz_policy = ACLAuthorizationPolicy()
        config.set_authentication_policy(authn_policy)
        config.set_authorization_policy(authz_policy)

        # session factory
        session_factory = SignedCookieSessionFactory('foo')
        config.set_session_factory(session_factory)

        config.add_renderer(name='rest', factory='nti.app.environments.renderers.renderers.DefaultRenderer')
        config.add_renderer(name='.rml', factory="nti.app.environments.renderers.pdf.PDFRendererFactory")

        config.add_traverser( ZopeResourceTreeTraverser )

        config.scan(ignore=[_ignore_tests_scan_callable, 'nti.app.environments.tasks'])

    return config
