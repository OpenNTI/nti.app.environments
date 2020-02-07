import random

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from zope import component

from zope.cachedescriptors.property import Lazy

from nti.externalization.interfaces import LocatedExternalDict\

from nti.app.environments.auth import is_admin_or_account_manager

from nti.app.environments.interfaces import ISiteDomainFactory

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.views.base import BaseView
from nti.app.environments.views.utils import raise_json_error
from nti.app.environments.views.utils import is_dns_name_available


EXCLUDED_SUBDOMAIN_SUFFIX = ('6969', '666', '420')

def _generate_digits(length=4):
    return ''.join(["{}".format(random.randint(0, 9)) for _ in range(0, length)])


@view_config(renderer='rest',
             context=IOnboardingRoot,
             request_method='GET',
             name="check_dns_name")
class CheckDNSNameAvailableView(BaseView):

    def __call__(self):
        # This is the quick way to only allow authenticated user to access this view.
        # later may define a specific permission?
        userid = self.request.authenticated_userid
        if not userid:
            raise hexc.HTTPForbidden()

        params = self.request.params
        dns_name = self._get_param('dns_name', params)

        # Expect all dns names should be lower case. and belongs to expected domain.
        dns_name = dns_name.lower()

        # Skip checking for admin and management roles.
        if not is_admin_or_account_manager(userid, self.request):
            domain = component.getUtility(ISiteDomainFactory)()
            if not dns_name.endswith(domain):
                raise_json_error(hexc.HTTPUnprocessableEntity,
                                 "Invalid dns name.")

        sites_folder = get_sites_folder(self.context, self.request)
        is_available = is_dns_name_available(dns_name, sites_folder)

        result = LocatedExternalDict()
        result.__parent__ = self.context.__parent__
        result.__name__ = self.context.__name__
        result.update({'dns_name': dns_name,
                       'is_available': is_available})
        return result


@view_config(renderer='rest',
             context=IOnboardingRoot,
             request_method='GET',
             name="valid_domain")
class ValidDomainView(BaseView):

    @Lazy
    def sites_folder(self):
        return get_sites_folder(self.context, self.request)

    def _is_suffix_available(self, suffix):
        try:
            self._suffixes
        except AttributeError:
            self._suffixes = set()

        if suffix in self._suffixes:
            return False

        for x in EXCLUDED_SUBDOMAIN_SUFFIX:
            if x in suffix:
                return False

        self._suffixes.add(suffix)
        return True

    def _generate_dns_name(self, subdomain, domain, tries=9999):
        while tries > 0:
            tries -= 1
            suffix = _generate_digits()
            if not self._is_suffix_available(suffix):
                continue

            dns_name = '{}-{}.{}'.format(subdomain, suffix, domain)
            if is_dns_name_available(dns_name, self.sites_folder):
                return dns_name
        return None

    def __call__(self):
        userid = self.request.authenticated_userid
        if not userid:
            raise hexc.HTTPForbidden()

        subdomain = self._get_param('subdomain').lower()
        domain = component.getUtility(ISiteDomainFactory)()

        result = LocatedExternalDict()
        result.__parent__ = self.context.__parent__
        result.__name__ = self.context.__name__
        result.update({'subdomain': subdomain,
                       'domain': domain})

        # For admin/management, just no random suffix should be applied.
        if is_admin_or_account_manager(userid, self.request):
            dns_name = '{}.{}'.format(subdomain, domain)
            is_available = is_dns_name_available(dns_name, self.sites_folder)
            result.update({'dns_name': dns_name,
                           'is_available': is_available})
            return result

        dns_name = self._generate_dns_name(subdomain, domain)
        result.update({'dns_name': dns_name,
                       'is_available': bool(dns_name is not None)})
        return result
