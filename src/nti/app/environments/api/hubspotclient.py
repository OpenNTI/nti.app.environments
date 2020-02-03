import time

from nameparser import HumanName

from hubspot3 import Hubspot3
from hubspot3.error import HubspotNotFound
from hubspot3.error import HubspotError

from nti.app.environments.settings import HUBSPOT_API_KEY
from nti.app.environments.settings import HUBSPOT_PORTAL_ID

logger = __import__('logging').getLogger(__name__)


class HubspotClient(object):

    def __init__(self, apikey):
        self._client = Hubspot3(api_key=apikey)

    def _call(self, _callable, *args, **kwargs):
        logger.info("Begin %s.", _callable.__name__)
        start = time.perf_counter()
        try:
            response = _callable(*args, **kwargs)
        except HubspotNotFound:
            response = None
        except HubspotError:
            logger.exception("Unknown error.")
            raise

        elapsed = time.perf_counter() - start
        logger.info("End %s, elapsed: %s seconds.", _callable.__name__, elapsed)
        return response

    def fetch_contact_by_email(self, email):
        contact = self._call(self._client.contacts.get_contact_by_email,
                             email,
                             properties=['email', 'firstname', 'lastname'],
                             params={'showListMemberships': 'false',
                                     'propertyMode':'value_only'})
        if not contact:
            logger.warning("No hubspot contact found with email: {}".format(email))
            return None

        props = contact['properties']

        first = props['firstname']['value'].strip() if 'firstname' in props else None
        last = props['lastname']['value'].strip() if 'lastname' in props else None
        name = "{} {}".format(first, last) if first and last else first or last
        return {'canonical-vid': contact['canonical-vid'],
                'email': props['email']['value'],
                'name': name or ''}

    def upsert_contact(self, email, name):
        logger.info("Upserting contact to hubspot with email: %s, name: %s.", email, name)
        firstname, lastname = _split_name(name)

        props = []
        for prop_name, prop_value in (('firstname', firstname),
                             ('lastname', lastname)):
            props.append({'property': prop_name,
                          'value': prop_value})

        data = {'properties': props}
        result = self._call(self._client.contacts.create_or_update_by_email,
                            email,
                            data=data)
        # This shouldn't happen in practice unless the hubspot3 API is outdated.
        if result is None:
            logger.warning("Failed to upsert contact for email (%s) in hubspot.", email)
            return None

        return {'contact_vid': str(result['vid'])}


def _split_name(name):
    name = HumanName(name)
    return (name.first, name.last)


_hubspot_client =None

def get_hubspot_client():
    global _hubspot_client
    if _hubspot_client is None:
        _hubspot_client = HubspotClient(HUBSPOT_API_KEY)
    return _hubspot_client


def get_hubspot_profile_url(contact_vid):
    return "https://app.hubspot.com/contacts/{portal_id}/contact/{vid}".format(portal_id=HUBSPOT_PORTAL_ID,
                                                                               vid=contact_vid)
