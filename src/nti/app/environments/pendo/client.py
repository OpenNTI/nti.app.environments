import requests
import time

from zope import component
from zope import interface

from .interfaces import IPendoAccount
from .interfaces import IPendoClient

from nti.app.environments.interfaces import IOnboardingSettings

logger = __import__('logging').getLogger(__name__)

@interface.implementer(IPendoClient)
class PendoV1Client(object):

    def __init__(self, key):
        self.session = requests.Session()
        self.session.headers.update({'X-PENDO-INTEGRATION-KEY': key})

    def _account_id(self, account):
        if isinstance(account, str):
            return account
        return IPendoAccount(account).account_id

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

class _NoopPendoClient(PendoV1Client):

    def update_metadata_set(self, kind, group, payload):
        logger.info('Simulating post to pendo %s %s',
                  f'https://app.pendo.io/api/v1/metadata/{kind}/{group}/value',
                  payload)


def _dev_pendo_client():
    return _NoopPendoClient('secret')

def _live_pendo_client():
    settings = component.getUtility(IOnboardingSettings)
    try:
        key = settings['pendo_integration_key']
    except KeyError:
        return None
    return PendoV1Client(key)
