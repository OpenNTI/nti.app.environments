import requests
import time

from zope import component
from zope import interface

from zope.proxy import ProxyBase
from zope.proxy import getProxiedObject
from zope.proxy import non_overridable

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


@interface.implementer(IPendoClient)
class PendoV1Client(object):

    def __init__(self, key):
        self.session = requests.Session()
        self.session.headers.update({'X-PENDO-INTEGRATION-KEY': key})

    def as_account_id(self, account):
        """
        Determines if the client can be used to interact with the provided pendo account.
        account should be a string or something adaptable to an IPendoAccount
        """
        _account_id = _resolve_account_id(account)
        return _account_id

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
        payload = [{'accountId': self.as_account_id(account),
                    'values': values} for (account, values) in metadata.items()]
        return self.update_metadata_set('account', 'custom', payload)

class _NoopPendoClient(PendoV1Client):

    def update_metadata_set(self, kind, group, payload):
        logger.info('Simulating post to pendo %s %s',
                  f'https://app.pendo.io/api/v1/metadata/{kind}/{group}/value',
                  payload)

@interface.implementer(IPendoClient)
class BoundPendoClient(ProxyBase):
    """
    A pendo client that restricts account operations to a certain
    account (if provided).

    This is implemented as a proxy, calling through to a provided base
    client for the interactions with pendo.
    """

    __slots__ = ('_bound_account_id', )

    def __init__(self, client):
        super(BoundPendoClient, self).__init__(client)
        self.bind_account(None)
    
    def bind_account(self, account):
        """
        Bind the client to the provided account. Account should be a string
        or something adaptable to an IPendoAccount
        """
        self._bound_account_id = None if account is None else _resolve_account_id(account)

    @non_overridable
    def as_account_id(self, account):
        """
        Determines if the client can be used to interact with the provided pendo account.
        account should be a string or something adaptable to an IPendoAccount
        """
        _account_id = getProxiedObject(self).as_account_id(account)
        self.check_accountid(_account_id)
        return _account_id

    def check_accountid(self, account_id):
        if self._bound_account_id and account_id != self._bound_account_id:
            raise InvalidPendoAccount(account_id)
        return True

    @non_overridable
    def update_metadata_set(self, kind, group, payload):
        # Check the account in case we are bound and called directly
        for acm in payload:
            self.check_accountid(acm['accountId'])
        return getProxiedObject(self).update_metadata_set(kind, group, payload)
        
def _dev_pendo_client():
    return _NoopPendoClient('secret')

def _live_pendo_client():
    settings = component.getUtility(IOnboardingSettings)
    try:
        key = settings['pendo_integration_key']
    except KeyError:
        return None
    return PendoV1Client(key)

def _pendo_client_for_site(site):
    pendo = component.getUtility(IPendoClient)
    client = BoundPendoClient(pendo)
    client.bind_account(site)
    return client

def _pendo_client_for_test_site(site):
    """
    Return a pendo client for the site, but only
    if this is a test site. This is registered as an adapter
    when running in the asci-test environment. That system
    frequently tracks sites that line up with production sites,
    so we don't want to overwrite prod data, but we do need to
    sync sites created in that installation because product management
    uses those sites to test and validate their pendo guide flows.

    The hueristic we use here is to key off the domain name. We use
    the domain *.nextthot.com for sites generated out of asci-test
    so this function only returns client for sites that match that.
    """
    if [x for x in site.dns_names or [] if x.endswith('nextthot.com')]:
        return _pendo_client_for_site(site)
    return None
