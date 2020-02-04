import time

from nameparser import HumanName

from hubspot3 import Hubspot3
from hubspot3.error import HubspotNotFound
from hubspot3.error import HubspotError
from hubspot3.error import HubspotConflict

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
        except HubspotConflict:
            raise
        except HubspotError:
            logger.exception("Unknown error.")
            raise

        elapsed = time.perf_counter() - start
        logger.info("End %s, elapsed: %s seconds.", _callable.__name__, elapsed)
        return response

    def _fetch_contact_by_email(self, email):
        return self._call(self._client.contacts.get_by_email,
                          email,
                          properties=['email', 'firstname', 'lastname'],
                          params={'showListMemberships': 'false',
                                  'propertyMode':'value_only'})

    def _create_contact(self, email, name, product_interest):
        firstname, lastname = _split_name(name)
        data = self._build_data(email=email,
                                firstname=firstname,
                                lastname=lastname,
                                product_interest=product_interest)
        return self._call(self._client.contacts.create,
                          data)

    def fetch_contact_by_email(self, email):
        contact = self._fetch_contact_by_email(email)
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

    def create_contact(self, email, name, product_interest):
        logger.info("Inserting a new contact to hubspot with email: %s, name: %s, product_interest: %s.",
                    email, name, product_interest)
        try:
            firstname, lastname = _split_name(name)
            data = self._build_data(email=email,
                                    firstname=firstname,
                                    lastname=lastname,
                                    product_interest=product_interest)
            result = self._call(self._client.contacts.create,
                                data)
        except HubspotConflict:
            logger.warn("Existing hubspot contact: %s.", email)
            result = None

        if result is None:
            logger.warn("Failed to insert contact to hubspot with email: %s, name: %s, product_interest: %s.",
                        email, name, product_interest)
        return result

    def update_contact(self, email, product_interest):
        logger.info("Updating contact to hubspot with email: %s, product_interest: %s.",
                    email, product_interest)
        data = self._build_data(product_interest=product_interest)

        # update_by_email returns 204 No Content if successfully.
        result = self._call(self._client.contacts.update_by_email,
                            email,
                            data)
        if result is None:
            logger.warn("Failed to update contact to hubspot with email: %s, product_interest: %s.",
                        email, product_interest)
        return result

    def upsert_contact(self, email, name, product_interest='LMS'):
        result = self._fetch_contact_by_email(email)
        if result is None:
            result = self.create_contact(email, name, product_interest)
        else:
            result = self.update_contact(email, product_interest)
            # Needs to fetch the latest contact_vid.
            if result is not None:
                result = self._fetch_contact_by_email(email)

        if result is None:
            return None

        return {'contact_vid': str(result['vid'])}

    def _build_data(self, email=None, firstname=None, lastname=None, product_interest=None):
        props = []
        for prop_name, prop_value in (('email', email),
                                      ('firstname', firstname),
                                      ('lastname', lastname),
                                      ('product_interest', product_interest)):
            if prop_value is not None:
                props.append(self._build_property(prop_name, prop_value))
        return {'properties': props}

    def _build_property(self, prop_name, prop_value):
        return {'property': prop_name,
                'value': prop_value}


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
