import gevent
import transaction

from zope import interface
from zope import component

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from . import PENDO_SITE_STATUS
from . import PENDO_SITE_LICENSE_TYPE
from . import PENDO_SITE_LICENSE_FREQUENCY
from . import PENDO_SITE_LICENSE_SEATS
from . import PENDO_SITE_LICENSE_INSTRUCTOR_ADDON_SEATS
from . import PENDO_SITE_TRIAL_ENDDATE

from . import serialize_datetime

from .interfaces import IPendoClient

from nti.app.environments.interfaces import ITransactionRunner

from nti.app.environments.models.interfaces import ISiteLicense
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ILMSSite

from nti.app.environments.pendo.interfaces import MissingPendoAccount

from nti.app.environments.models.utils import get_sites_folder

logger = __import__('logging').getLogger(__name__)

UNLIMITED_SEATS = 65535

def make_pendo_status_payload(site):
    payload = {}
    payload[PENDO_SITE_STATUS] = site.status

    license = site.license
        
    payload[PENDO_SITE_LICENSE_TYPE] = license.license_name
    payload[PENDO_SITE_LICENSE_FREQUENCY] = getattr(license, 'frequency', 'unknown')
    payload[PENDO_SITE_LICENSE_SEATS] = getattr(license, 'seats', UNLIMITED_SEATS)
    payload[PENDO_SITE_LICENSE_INSTRUCTOR_ADDON_SEATS] = getattr(license, 'additional_instructor_seats', 0)

    if ITrialLicense.providedBy(license):
        payload[PENDO_SITE_TRIAL_ENDDATE] = serialize_datetime(license.end_date)
        
    return payload

class PendoSiteStatusPublisher(object):

    def __init__(self, site):
        self._site = site

    def _build_payload(self):
        return make_pendo_status_payload(self._site)
    
    def __call__(self):
        logger.info('Will publish site status information to pendo for site %s', self._site)

        pendo = component.queryUtility(IPendoClient)
        if pendo is None:
            logger.warn('No pendo client installed. Not publishing to pendo')
            return

        return pendo.set_metadata_for_accounts({self._site: self._build_payload()})

def _publish_to_pendo(success, siteid):
    """
    Called as an afterCommitHook to push site status
    and license information to pendo. This executes
    in a greenlet after the request transaction has committed
    and returned. We could also throw this out on to a celery
    queue at some point.
    """

    if not success:
        return
    
    tx_runner = component.getUtility(ITransactionRunner)

    def _publish():
        def _do_publish(root):
            # TODO we may want to capture the last modified times
            # here and abort if those changed since we were spawned?
            # There's a subtle race condition here as we can't
            # guarentee anything about the order we are executing in. 
            sites = get_sites_folder(root)
            site = sites[siteid]
            try:
                PendoSiteStatusPublisher(site)()
            except MissingPendoAccount:
                logger.warn("ds_site_id not found for site with id: %s", siteid)


        tx_runner(_do_publish, side_effect_free=True)

    gevent.spawn(_publish)

def _send_site_status_to_pendo(site):
    sid = site.id
    transaction.get().addAfterCommitHook(
            _publish_to_pendo, args=(sid,), kws=None
    )

@component.adapter(ILMSSite, IObjectModifiedEvent)
def _on_site_modified(site, event):
    _send_site_status_to_pendo(site)
    
@component.adapter(ISiteLicense, IObjectModifiedEvent)
def _on_site_license_modified(license, event):
    site = component.queryAdapter(license, ILMSSite)
    # We may not be able to find a site when a new license is created.
    # in that case IObjectModifiedEvent fire on the license before it is given
    # to the site. We can ignore that here, because we will get an
    # IObjectModifiedEvent on the site when the new license gets set.
    if site is not None:
        _send_site_status_to_pendo(site)
