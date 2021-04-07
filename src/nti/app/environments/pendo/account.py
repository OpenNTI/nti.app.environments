from urllib.parse import quote as encode_part

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
    def _ds_id(self):
        """
        Unfortunately, while that matches ILMSSite.id in most cases,
        it doesn't always match.

        TODO we need to sync these ids up or capture the ds site as
        a first order thing.
        """

        # We can't distinguish when we can just use self.site.id
        # right now can we???

        # UGH and if the site isn't active we can't figure that out?
        if self._site.ds_site_id:
            return self._site.ds_site_id

        # If we haven't captured a ds_site_id we can try and ping the site
        # ping the site for it. This is a shim until we get all the data fixed
        # up approrpiately.
        # TODO remove this when possible
        client = NTClient(self._site)
        pong = client.dataserver_ping()
        return pong['Site'] if pong else None

    @Lazy
    def account_id(self):
        """
        PendoAccount identifiers are tricky, in particular if parent
        accounts are enabled in pendo. Our install enables this.

        To push data through the api when parent accounts are enabled
        you need an identifier of the form
        <parentaccountid>::<accountid>. Recall accountid is _ds_id.
        Currently we aren't exposing parent information, and it isn't
        clear if that should be explicitly specified or derived from
        the site heirarchy. So in this case we take _ds_id as the
        parent as well, i.e. we don't group them.
        """

        if not self._ds_id:
            return None
        return '%s::%s' % (self._ds_id, self._ds_id)

    @Lazy
    def account_web_url(self):
        return 'https://app.pendo.io/account/%s' % encode_part(self.account_id)
    
    def __init__(self, site):
        self._site = site


def _test_pendo_account(site):
    if 'nextthot.com' in site.dns_names[0]:
        return PendoAccount(site)
    return None
