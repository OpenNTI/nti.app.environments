from urllib.parse import urlunparse
from urllib.parse import urlparse
from urllib.parse import urljoin
from urllib.parse import parse_qs
from urllib.parse import urlencode

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from ZODB.interfaces import IBroken

from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.interfaces import IOnboardingRootPrincipalRoleManager
from nti.app.environments.interfaces import ISiteDomainFactory
from nti.app.environments.interfaces import ISiteLinks

from nti.app.environments.models.interfaces import ISetupStateSuccess

from nti.environments.management.interfaces import ISettings

from nti.externalization.interfaces import IExternalObject

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IOnboardingRootPrincipalRoleManager)
class OnboardingRootPrincipalRoleManager(AnnotationPrincipalRoleManager):
    pass


@interface.implementer(IOnboardingRootPrincipalRoleManager)
@component.adapter(IOnboardingRoot)
def _principal_role_manager(onboarding_root):
    return OnboardingRootPrincipalRoleManager(onboarding_root)

@component.adapter(IBroken)
@interface.implementer(IExternalObject)
class BrokenExternalObject(object):
    """
    Renders broken object. This is mostly for (legacy) logging purposes, as the general
    NonExternalizableObject support catches these now.

    TODO: Consider removing this. Is the logging worth it? Alternately, should the
    NonExternalizableObject adapter be at the low level externization package or
    up here?
    """

    def __init__(self, broken):
        self.broken = broken

    def toExternalObject(self, **unused_kwargs):
        # Broken objects mean there's been a persistence
        # issue. Ok to log it because since its broken, it won't try to call
        # back to us
        logger.debug("Broken object found %s, %s",
                     type(self.broken), self.broken)
        result = {'Class': 'BrokenObject'}
        return result


@interface.implementer(ISiteLinks)
class SiteLinks(object):

    def __init__(self, site, request):
        self.site = site
        self.request = request

    @Lazy
    def preferred_dns(self):
        return self.site.dns_names[0] if self.site.dns_names else None

    @Lazy
    def application_url(self):
        host = self.preferred_dns
        return urlunparse(('https', host, '/app', None, None, None))

    @Lazy
    def complete_account_url(self):
        """
        This is complex as we've ducktaped a large amount of existing
        functionality together to make this work. The user finishes
        creating their account by accepting a site invitation which
        was generated as part of setup and can be found on the ILMSSite.setup_state
        object. The typical invitation flow is to hit the
        dataserver2 accept link, which sends the user to the normal login/account creation
        flow. In our case we have a slightly custom account creation page[1] we want to hit
        so we have to tell the accept invitation where to take us on success.

        But wait, there is more, this system wants to know when the
        user accepts the invitation. So that behaviour is "expected"
        and natural if they come back through this flow after having
        already done it (via email or site recovery).  There's no
        mechanism for us to be told the invite was accepted so on
        acceptance, instead of taking the user to the app, we bounce them
        through a view here, and then on to the app. In summary:

        Hop 1: <site>/dataserver2/accept-site-invitation?success=/logon/accept/invitation
        Hop 2: <site>/logon/signup?return=/onboarding/site-invitation/finished
        Hop 3: /onboarding/site-invitation/finished?return=/app
        Hop 4: <site>/app

        This ultimately ends up as one giant nested ball of return urls.

        [1] this may become the general behaviour in the future.

        """

        # First off, this only makes sense if setup is completed succesfully
        # AND we have an invite url.
        if not ISetupStateSuccess.providedBy(self.site.setup_state):
            return None

        invite_href = self.site.setup_state.site_info.admin_invitation
        if not invite_href:
            return None

        # Now we have to build things up backwards.

        # The last hop is through us to mark as accepted, and then to the app
        query = {'return': self.application_url}
        rfstate = self.request.session.get('onboarding.continue_to_site.state', None) if self.request else None
        if rfstate:
            query['state'] = rfstate
        # See nti.app.environments.views.sites.ContinueToSite

        ping_back = self.request.resource_url(self.site, '@@mark_invite_accepted',
                                              query=query)

        # Prior to that the user gets sent to the login accept view. Note this has to be relative
        # to the app host
        account_creation = urljoin(self.application_url, '/login/account-setup')
        parsed = urlparse(account_creation)
        parsed = parsed._replace(scheme='', netloc='', query=urlencode({'return': ping_back}))
        account_creation = urlunparse(parsed)

        # Lastly make our invite href host absolute since we are changing domains here
        # also add the success return parameter. Note invite_href almost certainly
        # already has query parameters on it so we are extra careful
        invite_href = urljoin(self.application_url, invite_href)
        parsed = urlparse(invite_href)
        params = parse_qs(parsed.query)
        params['success'] = account_creation
        parsed = parsed._replace(query=urlencode(params, doseq=True))
        return urlunparse(parsed)


@interface.implementer(ISiteDomainFactory)
class SiteDomainFactory(object):

    def __call__(self):
        settings = component.getUtility(ISettings)
        result = 'nextthought.io'
        try:
            result = settings['dns']['base_domain']
        except KeyError:
            pass
        return result
