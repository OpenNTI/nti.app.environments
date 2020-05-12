import pytz

from pyramid.threadlocal import get_current_request

from zope import component

from nti.app.environments.models.interfaces import ISetupStateSuccess
from nti.app.environments.models.interfaces import ILMSSiteCreatedEvent
from nti.app.environments.models.interfaces import ILMSSiteSetupFinished
from nti.app.environments.models.interfaces import ILMSSiteOwnerCompletedSetupEvent

from nti.app.environments.models.utils import get_sites_with_owner

from . import get_hubspot_client

from . import HUBSPOT_FIELD_ASCI_PHONE
from . import HUBSPOT_FIELD_ASCI_SITE_COMPLETED
from . import HUBSPOT_FIELD_ASCI_SITE_DETAILS
from . import HUBSPOT_FIELD_ASCI_SITE_GOTO

logger = __import__('logging').getLogger(__name__)

def _as_hubspot_timestamp(dt, hubspot_tz='US/Central'):
    # Note hubspot wants times in milliseconds. It stores them internally as UTC
    # and displays in the timezone of the user. The documentation is unclear, but
    # empirical evidence suggests that they expect the inbound timestamps to also
    # be in the accounts timezone, not utc...
    # https://developers.hubspot.com/docs/faq/how-should-timestamps-be-formatted-for-hubspots-apis
    utc_date = pytz.utc.localize(dt)
    hubspot_dt = utc_date.astimezone(pytz.timezone(hubspot_tz))
    return int(hubspot_dt.timestamp()*1000)

@component.adapter(ILMSSiteCreatedEvent)
def _sync_new_site_to_hubspot(event):
    hubspot_client = get_hubspot_client()
    if hubspot_client is None:
        logger.warn('No configured hubspot client. Not syncing')
        return
    
    site = event.site
    customer = site.owner

    # TODO We're making an assumption in the hubspot data that there is only one site per customer here.
    # That's true right now for external users, but not for internal users.
    if len(list(get_sites_with_owner(customer))) > 1:
        logger.warn('Customer %s already has sites. Not overwriting hubspot info', customer.email)
        return

    logger.info('Syncing site details url to hubspot for contact %s', customer.email)

    request = get_current_request()

    props = {
        HUBSPOT_FIELD_ASCI_SITE_DETAILS: request.resource_url(site, '@@details')
    }
    
    hubspot_client.update_contact_with_properties(customer.email, props)

@component.adapter(ILMSSiteSetupFinished)
def _sync_finished_site_to_hubspot(event):
    hubspot_client = get_hubspot_client()
    if hubspot_client is None:
        logger.warn('No configured hubspot client. Not syncing')
        return

    site = event.site
    if not ISetupStateSuccess.providedBy(site.setup_state):
        return

    if not site.setup_state.site_info.admin_invitation:
        return

    customer = site.owner
    
    # TODO We're making an assumption in the hubspot data that there is only one site per customer here.
    # That's true right now for external users, but not for internal users.
    if len(list(get_sites_with_owner(customer))) > 1:
        logger.warn('Customer %s already has sites. Not overwriting hubspot info', customer.email)
        return

    logger.info('Syncing site goto url to hubspot for contact %s', customer.email)

    request = get_current_request()

    props = {
        HUBSPOT_FIELD_ASCI_SITE_GOTO: request.resource_url(site, '@@GoToSite')
    }
    
    
    hubspot_client.update_contact_with_properties(customer.email, props)

@component.adapter(ILMSSiteOwnerCompletedSetupEvent)
def _sync_setup_completed_to_hubspot(event):
    hubspot_client = get_hubspot_client()
    if hubspot_client is None:
        logger.warn('No configured hubspot client. Not syncing')
        return
    
    site = event.site
    customer = site.owner

    # TODO We're making an assumption in the hubspot data that there is only one site per customer here.
    # That's true right now for external users, but not for internal users.
    if len(list(get_sites_with_owner(customer))) > 1:
        logger.warn('Customer %s already has sites. Not overwriting hubspot info', customer.email)
        return

    logger.info('Syncing setup completed time to hubspot for contact %s', customer.email)

    
    props = {
        HUBSPOT_FIELD_ASCI_SITE_COMPLETED: _as_hubspot_timestamp(event.completed_at)
    }

    hubspot_client.update_contact_with_properties(customer.email, props)
