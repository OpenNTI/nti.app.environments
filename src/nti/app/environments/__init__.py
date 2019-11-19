import pyramid_zcml

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from pyramid.config import Configurator

from pyramid.session import SignedCookieSessionFactory

from pyramid_zodbconn import get_connection

from zope.component import getGlobalSiteManager

import zope.i18nmessageid

from .models import appmaker
from .settings import init_app_settings

# TODO what setup is missing here to make this work
MessageFactory = zope.i18nmessageid.MessageFactory('nti.app.environments')


def root_factory(request):
    conn = get_connection(request)
    return appmaker(conn.root())


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Use ZCA global site manager
    globalreg = getGlobalSiteManager()
    with Configurator(registry=globalreg) as config:
        config.setup_registry(settings=settings)
        settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'
        config.include(pyramid_zcml)
        config.include('pyramid_tm')
        config.include('pyramid_retry')
        config.include('pyramid_zodbconn')
        config.set_root_factory(root_factory)
        config.include('pyramid_chameleon')
        config.include('pyramid_mako')
        config.include('.routes')
        config.load_zcml('configure.zcml')

        
        # security policies
        authn_policy = AuthTktAuthenticationPolicy('foo',
                                                   hashalg='sha512')
        authz_policy = ACLAuthorizationPolicy()
        config.set_authentication_policy(authn_policy)
        config.set_authorization_policy(authz_policy)

        # session factory
        session_factory = SignedCookieSessionFactory('foo')
        config.set_session_factory(session_factory)

        # initialize global constants
        init_app_settings(settings)

        config.scan()
    return config.make_wsgi_app()
