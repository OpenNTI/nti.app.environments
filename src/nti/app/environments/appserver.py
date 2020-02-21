import os
import time
import gevent
import transaction

from pyramid_zodbconn import get_connection

from pyramid.interfaces import IRequestFactory
from pyramid.request import Request
from pyramid.threadlocal import RequestContext

from zope import component
from zope import interface

from zope.app.appsetup.appsetup import database
from zope.app.appsetup.appsetup import multi_database

from zope.app.publication.zopepublication import ZopePublication

from ZODB.interfaces import IDatabase
from ZODB.interfaces import IConnection

from .interfaces import ITransactionRunner
from .interfaces import IOnboardingServer
from .interfaces import IOnboardingSettings

from .models import ROOT_KEY

from .models.interfaces import ISetupStatePending

from .models.utils import get_sites_folder

from .utils import query_setup_state

logger = __import__('logging').getLogger(__name__)


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


def spawn_sites_setup_state_watchdog(registry):
    """
    Spawn a greenlet to query the setup state for pending sites every 10 mins.
    For reducing the conflicts within multiple workers, a randomly sleep time
    is set for each worker.
    """
    # A monotonic series, unlikely to wrap when we spawned
    my_sleep_adjustment = os.getpid() % 20
    if os.getpid() % 2:  # if even, go low
        my_sleep_adjustment = -my_sleep_adjustment

    sleep_time = 10*60 + my_sleep_adjustment

    tx_runner = component.getUtility(ITransactionRunner)

    def _query_setup_state():
        logger.info("[Worker %s] querying the setup state for pending sites every %s mins %s seconds.",
                    os.getpid(),
                    sleep_time // 60,
                    sleep_time % 60)

        while True:
            gevent.sleep(sleep_time)
            try:
                def _do_query_setup_state(root):
                    request = _make_dummy_request(registry, root)

                    with RequestContext(request) as request:
                        t0 = time.time()
                        folder = get_sites_folder(root)
                        sites = [x for x in folder.values() if ISetupStatePending.providedBy(x.setup_state)]
                        if sites:
                            query_setup_state(sites, request)
                            logger.info('Performed querying setup state on %s sites (%.2f)',
                                        len(sites),
                                        time.time() - t0 )

                tx_runner(_do_query_setup_state, retries=5, sleep=0.1)
            except transaction.interfaces.TransientError:
                logger.debug("Trying sites setup state query later.", exc_info=True)
                continue

    return gevent.spawn(_query_setup_state)


def _make_dummy_request(registry, root):
    base_url = registry.getUtility(IOnboardingSettings)['application_url']
    req_factory = component.queryUtility(IRequestFactory, default=Request)
    request = req_factory.blank('/', base_url=base_url)
    request.registry = registry

    # At least the email template requires this.
    request.context = root

    # Making sure request has the same connection as the one created earlier in current transaction.,
    # such that it will not try to get a new one when we load objects from the current request,
    # which may result in InvalidObjectReference error when submit the transaction.
    request._primary_zodb_conn = IConnection(root)
    return request


def root_folder(request):
    conn = get_connection(request)

    server = component.getUtility(IOnboardingServer)
    return server.root_onboarding_folder(conn)
