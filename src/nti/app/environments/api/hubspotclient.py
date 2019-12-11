import time

from hubspot3 import Hubspot3
from hubspot3.error import HubspotNotFound
from hubspot3.error import HubspotError

from nti.app.environments.settings import HUBSPOT_API_KEY

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

        first = props['firstname']['value'] if 'firstname' in props else None
        last = props['lastname']['value'] if 'lastname' in props else None
        name = "{} {}".format(first, last) if first and last else first or last
        return {'canonical-vid': contact['canonical-vid'],
                'email': props['email']['value'],
                'name': name or ''}


_hubspot_client =None

def get_hubspot_client():
    global _hubspot_client
    if _hubspot_client is None:
        _hubspot_client = HubspotClient(HUBSPOT_API_KEY)
    return _hubspot_client
