from zope import interface

from zope.cachedescriptors.property import Lazy

from nti.app.environments.api.siteinfo import NTClient

from .interfaces import IPendoAccount

@interface.implementer(IPendoAccount)
class PendoAccount(object):
    """
    An adapter from ILMSSite to IPendoAccount
    """

    @Lazy
    def account_id(self):
        """
        The pendo account for a site is the ds siteid.
        Unfortunately, while that matches ILMSSite.id in most cases,
        it doesn't always match.

        TODO we need to sync these ids up or capture the ds site as
        a first order thing.
        """

        # We can't distinguish when we can just use self.site.id
        # right now can we???

        # UGH and if the site isn't active we can't figure that out?
        
        client = NTClient(self._site)
        return client.dataserver_ping()['Site']

    @Lazy
    def account_web_url(self):
        return 'https://app.pendo.io/parentAccount/%s' % self.account_id
    
    def __init__(self, site):
        self._site = site
