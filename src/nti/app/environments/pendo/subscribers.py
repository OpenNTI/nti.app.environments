import gevent
import transaction

from zope import interface
from zope import component

from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from . import PENDO_SITE_STATUS
from . import PENDO_SITE_LICENSE_TYPE
from . import PENDO_SITE_LICENSE_FREQUENCY
from . import PENDO_SITE_LICENSE_SEATS
from . import PENDO_SITE_TRIAL_ENDDATE

from . import serialize_datetime

from .interfaces import IPendoClient

from nti.app.environments.interfaces import ITransactionRunner

from nti.app.environments.models.interfaces import ISiteLicense
from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import ILMSSite

from nti.app.environments.models.utils import get_sites_folder

logger = __import__('logging').getLogger(__name__)

UNLIMITED_SEATS = 65535

class PendoSiteStatusPublisher(object):

    def __init__(self, site):
        self._site = site

    def _build_payload(self):
        payload = {}
        payload[PENDO_SITE_STATUS] = self._site.status

        license = self._site.license
        
        payload[PENDO_SITE_LICENSE_TYPE] = license.license_name
        payload[PENDO_SITE_LICENSE_FREQUENCY] = getattr(license, 'frequency', 'unknown')
        payload[PENDO_SITE_LICENSE_SEATS] = getattr(license, 'seats', UNLIMITED_SEATS)

        if ITrialLicense.providedBy(license):
            payload[PENDO_SITE_TRIAL_ENDDATE] = serialize_datetime(license.end_date)
        
        return payload
    
    def __call__(self):
        logger.info('Will publish site status information to pendo for site %s', self._site)

        pendo = component.queryUtility(IPendoClient)
        if pendo is None:
            logger.warn('No pendo client installed. Not publishing to pendo')
            return

        return pendo.set_metadata_for_accounts({self._site: self._build_payload()})

def _publish_to_pendo(success, siteid):

    if not success:
        return
    
    tx_runner = component.getUtility(ITransactionRunner)

    def _publish():
        def _do_publish(root):
            sites = get_sites_folder(root)
            site = sites[siteid]
            PendoSiteStatusPublisher(site)()

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
    # in that case IObjectModifiedEvent fires on the license is given
    # to the site. We can ignore that here, becuase we will get an
    # IObjectModifiedEvent on the site when the new license gets set.
    if site is not None:
        _send_site_status_to_pendo(site)
