import time

from nameparser import HumanName

from hubspot3 import Hubspot3
from hubspot3.error import HubspotNotFound
from hubspot3.error import HubspotError
from hubspot3.error import HubspotConflict

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.app.environments.api.interfaces import IHubspotClient

from nti.app.environments.settings import HUBSPOT_API_KEY
from nti.app.environments.settings import HUBSPOT_PORTAL_ID

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IHubspotClient)
class HubspotClient(object):

    def __init__(self, apikey):
        self.apikey = apikey

    @Lazy
    def _client(self):
        return Hubspot3(api_key=self.apikey)

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

    def _fetch_contact_by_email(self, email, product_interest=False):
        props = ['email', 'firstname', 'lastname']
        if product_interest:
            props.append('product_interest')
        return self._call(self._client.contacts.get_by_email,
                          email,
                          properties=props,
                          params={'showListMemberships': 'false',
                                  'propertyMode':'value_only'})

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
            data = self._build_data(email=email,
                                    name=name,
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

    def update_contact(self, email, name, product_interest):
        logger.info("Updating contact to hubspot with email: %s, name: %s, product_interest: %s.",
                    email, name, product_interest)
        data = self._build_data(name=name,
                                product_interest=product_interest)

        # update_by_email returns 204 No Content if successfully.
        result = self._call(self._client.contacts.update_by_email,
                            email,
                            data)
        if result is None:
            logger.warn("Failed to update contact to hubspot with email: %s, name: %s, product_interest: %s.",
                        email, name, product_interest)
        return result

    def _new_interest(self, result, product_interest):
        interest = result['properties'].get('product_interest') or {}
        interest = interest.get('value')
        interest = interest.split(';') if interest else []
        if product_interest not in interest:
            interest.append(product_interest)
        return ';'.join(interest)

    def upsert_contact(self, email, name, product_interest='LMS'):
        logger.info("Upserting contact to hubspot for email: %s.", email)
        result = self._fetch_contact_by_email(email, product_interest=True)
        if result is None:
            result = self.create_contact(email, name, product_interest)
        else:
            interest = self._new_interest(result, product_interest)
            result = self.update_contact(email, name, interest)

            # Fetch the latest contact_vid in case its contact_vid changes.
            if result is not None:
                result = self._fetch_contact_by_email(email)

        if result is None:
            logger.info("Failing to upsert contact to hubspot for email: %s.", email)
            return None

        return {'contact_vid': str(result['vid'])}

    def _build_data(self, email=None, name=None, product_interest=None):
        firstname, lastname = _split_name(name) if name else (None, None)
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


@interface.implementer(IHubspotClient)
class DevModeHubspotClient(HubspotClient):

    def upsert_contact(self, email, name, product_interest='LMS'):
        if not email.endswith('@nextthought.com'):
            logger.info("In devmode, only contacts that end with @nextthought.com can be created or updated.")
            return
        return super(DevModeHubspotClient, self).upsert_contact(email, name, product_interest)


@interface.implementer(IHubspotClient)
def _hubspot_client_factory():
    return HubspotClient(HUBSPOT_API_KEY)


@interface.implementer(IHubspotClient)
def _devmode_hubspot_client_factory():
    return DevModeHubspotClient(HUBSPOT_API_KEY)


def _split_name(name):
    name = HumanName(name)
    return (name.first, name.last)


_hubspot_client =None

def get_hubspot_client():
    return component.getUtility(IHubspotClient)


def get_hubspot_profile_url(contact_vid):
    return "https://app.hubspot.com/contacts/{portal_id}/contact/{vid}".format(portal_id=HUBSPOT_PORTAL_ID,
                                                                               vid=contact_vid)
