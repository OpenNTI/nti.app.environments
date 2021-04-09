import requests
import time

from zope import component
from zope import interface

from .interfaces import IPendoAccount
from .interfaces import IPendoClient

from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.pendo.interfaces import InvalidPendoAccount
from nti.app.environments.pendo.interfaces import MissingPendoAccount


logger = __import__('logging').getLogger(__name__)


def _resolve_account_id(account):
    if not isinstance(account, str):
        account = IPendoAccount(account, None)
        account = account.account_id if account else None
                
    if not account:
        raise MissingPendoAccount('Must provide an account id or IPendoAccount with an account_id', account)
    return account

class _BoundPendoClientMixin(object):

    _bound_account_id = None
    
    def bind_account(self, account):
        """
        Bind the client to the provided account. Account should be a string
        or something adaptable to an IPendoAccount
        """
        self._bound_account_id = None if account is None else _resolve_account_id(account)

    def as_account_id(self, account):
        """
        Determines if the client can be used to interact with the provided pendo account.
        account should be a string or something adaptable to an IPendoAccount
        """
        _account_id = _resolve_account_id(account)
        self.check_accountid(_account_id)
        return _account_id

    def check_accountid(self, account_id):
        if self._bound_account_id and account_id != self._bound_account_id:
            raise InvalidPendoAccount(account_id)
        return True

@interface.implementer(IPendoClient)
class PendoV1Client(_BoundPendoClientMixin):

    def __init__(self, key):
        self.session = requests.Session()
        self.session.headers.update({'X-PENDO-INTEGRATION-KEY': key})

    def update_metadata_set(self, kind, group, payload):
        logger.info('Updating pendo %s metadata fields for %s. Sending payload of length %i', group, kind, len(payload))
        # Check the account in case we are bound and called directly
        for acm in payload:
            self.check_accountid(acm['accountId'])
        
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
        payload = [{'accountId': self.as_account_id(account),
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
