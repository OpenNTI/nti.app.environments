import pyramid_zcml

from pyramid.authorization import ACLAuthorizationPolicy

from pyramid.config import Configurator

from pyramid.session import SignedCookieSessionFactory

from pyramid.tweens import EXCVIEW

from zope.component import getGlobalSiteManager

import zope.i18nmessageid as zope_i18nmessageid

from nti.externalization.extension_points import set_external_identifiers

from .appserver import OnboardingServer

from .auth import AuthenticationPolicy

from .interfaces import IOnboardingServer

from .models.interfaces import IOnboardingRoot

from .settings import init_app_settings

# TODO what setup is missing here to make this work
MessageFactory = zope_i18nmessageid.MessageFactory('nti.app.environments')

# Override the hook in nti.ntiids,
# such that no OID/NTIIDs returned for externalization.
import nti.ntiids
def set_hook():
    hook = getattr(set_external_identifiers, 'sethook')
    hook(lambda context, result: None)
set_hook()


def root_factory(request):
    return IOnboardingRoot(request).__parent__


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Use ZCA global site manager
    globalreg = getGlobalSiteManager()
    with Configurator(registry=globalreg) as config:
        config.setup_registry(settings=settings)

        # initialize global constants
        init_app_settings(settings)

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

        
        # security policies
        authn_policy = AuthenticationPolicy('foo',
                                            hashalg='sha512')
        authz_policy = ACLAuthorizationPolicy()
        config.set_authentication_policy(authn_policy)
        config.set_authorization_policy(authz_policy)

        # session factory
        session_factory = SignedCookieSessionFactory('foo')
        config.set_session_factory(session_factory)

        config.scan()

    # We've let pyramid_zodbconn open the databases and set them in the registry
    # https://github.com/Pylons/pyramid_zodbconn/blob/68419e05a19acfc611e1dd81f79acc2a88d6e81d/pyramid_zodbconn/__init__.py#L190
    # Our OnboardingServer object will handle the rest of the setup and registration.
    #
    # Another approach is to use our own zodb_conn_tween like we do for other apps. One noticible difference
    # is that tween is able to put the transaction in explicit mode before a connection is open. I don't see
    # a hook in zodbconn that would let us do that. That may not matter for this use case.

    # Create and register our onboarding server
    server = OnboardingServer(config.registry._zodb_databases)
    getGlobalSiteManager().registerUtility(server, IOnboardingServer) 
    
    return config.make_wsgi_app()
