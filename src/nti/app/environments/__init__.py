import pyramid_zcml

from pyramid.authorization import ACLAuthorizationPolicy

from pyramid.config import Configurator

from pyramid.session import SignedCookieSessionFactory

from pyramid.tweens import EXCVIEW

from pyramid_zodbconn import get_connection

from zope.app.appsetup.appsetup import database
from zope.app.appsetup.appsetup import multi_database

from zope.component import getGlobalSiteManager

import zope.i18nmessageid as zope_i18nmessageid

from .auth import AuthenticationPolicy
from .models import appmaker
from .settings import init_app_settings

# TODO what setup is missing here to make this work
MessageFactory = zope_i18nmessageid.MessageFactory('nti.app.environments')


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
    #
    # Another approach is to use our own zodb_conn_tween like we do for other apps. One noticible difference
    # is that tween is able to put the transaction in explicit mode before a connection is open. I don't see
    # a hook in zodbconn that would let us do that. That may not matter for this use case.

    # We still need to do some setup to make sure things have a chance to react
    # to dbs being opened. For example things like zope.generations rely on IDatabaseOpenedWithRoot being fired.
    # zope.app.appsetup caries most of the load.

    # First we call nti.app.appsetup.appsetup.multi_database. This registers named IDatabase utilities
    # and sets up the activity monitor.
    # FIXME: do we have duplicate activity monitors now?
    
    # pyramid_zodbconn opened all our databases and put them in the
    # registry._zodb_databases
    class _db_factory(object):
        def __init__(self, name, db):
            self.name = name
            self.db = db

        def open(self):
            # already opened by zodbconn. Can we assert that status here?
            return self.db
    factories = [_db_factory(name, db) for name, db in config.registry._zodb_databases.items()]
    dbs, _ = multi_database(factories)

    # Now we call appsetup.database with all our dbs.
    # This notifies a db open event. This ends up calling
    # appsetup.bootstrap.bootStrapSubscriber which will ensure
    # a root object and in turn fire a IDatabaseOpenedWithRoot
    #
    # TODO bootStrapSubscriber creates a root folder if it doesn't exist
    # beneath ZopePublication.root_name (Application) which is sort of annoying.
    # It also makes it a SiteManager. Do we want/need that?
    # The alternative is to not register that subscriber and instead notify
    # IDatabaseOpenedWithRoot ourselves, then we let zope.generations install the
    # root folder as appropriate. Of course then we don't have a root which is a lie...
    for db in dbs:
        database(db)
    
    return config.make_wsgi_app()
