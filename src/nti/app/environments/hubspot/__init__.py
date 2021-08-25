from zope import component

from nti.app.environments.interfaces import IOnboardingSettings

from .interfaces import IHubspotClient

HUBSPOT_FIELD_ASCI_PHONE = 'nti_asci_customer_phone_number'
HUBSPOT_FIELD_ASCI_SITE_GOTO = 'nti_asci_site_goto_url'
HUBSPOT_FIELD_ASCI_SITE_GOTO_INTRO_COURSE = 'nti_asci_site_goto_intro_course_url'
HUBSPOT_FIELD_ASCI_SITE_DETAILS = 'nti_asci_internal_site_details'
HUBSPOT_FIELD_ASCI_SITE_COMPLETED = 'nti_asci_setup_completed'

def get_hubspot_client():
    return component.queryUtility(IHubspotClient)

def get_hubspot_profile_url(contact_vid):
    settings = component.getUtility(IOnboardingSettings)
    if 'hubspot_portal_id' not in settings:
        return None
    return "https://app.hubspot.com/contacts/{portal_id}/contact/{vid}".format(portal_id=settings['hubspot_portal_id'],
                                                                               vid=contact_vid)
