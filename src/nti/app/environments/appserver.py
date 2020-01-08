from pyramid_zodbconn import get_connection

from zope import component
from zope import interface

from zope.app.appsetup.appsetup import database
from zope.app.appsetup.appsetup import multi_database

from zope.app.publication.zopepublication import ZopePublication

from ZODB.interfaces import IDatabase

from .interfaces import IOnboardingServer

from .models import ROOT_KEY

@interface.implementer(IOnboardingServer)
class OnboardingServer(object):

    _db = None

    def __init__(self, _dbs):
        self.open_dbs(_dbs)

    @property
    def root_database(self):
        assert self._db is component.getUtility(IDatabase)
        return self._db

    def root_onboarding_folder(self, conn):
        return conn.root()[ZopePublication.root_name][ROOT_KEY]
        
    def open_dbs(self, dbs):
        # We currently expect a single db. Need to audit this function if going
        # to a multi db setup
        assert len(dbs) == 1, "Expecting a single db setup"
        
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
        factories = [_db_factory(name, db) for name, db in dbs.items()]
        dbs, _ = multi_database(factories)

        # Now we call appsetup.database with our root db.
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
        root_db = component.getUtility(IDatabase)
        
        assert root_db is dbs[0], 'Expect a single root db'

        database(root_db)        


def root_folder(request):
    conn = get_connection(request)

    server = component.getUtility(IOnboardingServer)
    return server.root_onboarding_folder(conn)
