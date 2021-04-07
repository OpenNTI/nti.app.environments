import requests
import time

from zope import component
from zope import interface

from .interfaces import IPendoAccount
from .interfaces import IPendoClient

from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.pendo.interfaces import MissingPendoAccount

logger = __import__('logging').getLogger(__name__)

@interface.implementer(IPendoClient)
class PendoV1Client(object):

    def __init__(self, key, track_key=None):
        self.session = requests.Session()
        self.session.headers.update({'X-PENDO-INTEGRATION-KEY': key})

        self.track_key = track_key

    def _account_id(self, account):
        if not isinstance(account, str):
            account = IPendoAccount(account).account_id
        if not account:
            raise MissingPendoAccount('Must provide an account id or IPendoAccount with an account_id', account)
        return account

    def update_metadata_set(self, kind, group, payload):
        logger.info('Updating pendo %s metadata fields for %s. Sending payload of length %i', group, kind, len(payload))
        start = time.time()
        resp = self.session.post(f'https://app.pendo.io/api/v1/metadata/{kind}/{group}/value', json=payload)
        resp.raise_for_status()
        logger.info('Updated pendo %s metadata fields for %s. Sent payload of length %i in %s seconds',
                    group, kind, len(payload), time.time() - start)
        result = resp.json()
        if result.get('failed'):
            #Some things may have gone through. Should we raise here???
            logger.warn('Errors when pushing pendo metadata. missing=(%s) errors=(%s)',
                        result.get('missing', ''), result.get('errors', ''))
        return result
        
    def set_metadata_for_accounts(self, metadata):
        """
        Set a set of values on a set of accounts.

        ``metadata`` is a map from IPendoAccount, or object adaptable to IPendoAccount, to
        dictionary of pendo attribute to pendo value.

        https://developers.pendo.io/docs/?python#set-value-for-a-set-of-agent-or-custom-fields
        """

        # Pendo wants a list of objects with an accountId and values so we have to pivot our metadata
        # mapping
        payload = [{'accountId': self._account_id(account),
                    'values': values} for (account, values) in metadata.items()]
        return self.update_metadata_set('account', 'custom', payload)

    def send_track_event(self, event, account, visitor, timestamp=None, properties=None, context={}):
        if not self.track_key:
            raise ValueError('No Pendo track key provided')

        account_id = self._account_id()

        payload = {
            'type': 'track',
            'event': event,
            'visitorId': visitor,
            'accountId': account_id,
            'timestamp': timestamp or int(time.time() * 1000),
            'properties': properties,
            'context': context or {}
        }

        logger.info('Sending pendo track event %s for %s in %s.', event, account_id, visitor)
        start = time.time()
        resp = self.session.post('https://app.pendo.io/data/track',
                                 json=payload,
                                 headers={'X-PENDO-INTEGRATION-KEY': self.track_key})
        resp.raise_for_status()
        logger.info('Sending pendo track event %s for %s in %s. Took %s seconds',
                    event, account_id, visitor, time.time() - start)
        result = resp.json()
        return result

class _NoopPendoClient(PendoV1Client):

    def update_metadata_set(self, kind, group, payload):
        logger.info('Simulating post to pendo %s %s',
                  f'https://app.pendo.io/api/v1/metadata/{kind}/{group}/value',
                  payload)

    def send_track_event(self, event, account, visitor, timestamp=None, properties=None, context={}):
        logger.info('Simulating pendo track event %s for %s in %s.', event, account, visitor)

def _dev_pendo_client():
    return _NoopPendoClient('secret')

def _live_pendo_client():
    settings = component.getUtility(IOnboardingSettings)
    try:
        key = settings['pendo_integration_key']
    except KeyError:
        return None
    track_key = settings.get('pendo_track_key', None)
    return PendoV1Client(key, track_key=track_key)
