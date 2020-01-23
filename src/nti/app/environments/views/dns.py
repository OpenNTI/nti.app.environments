from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from nti.externalization.interfaces import LocatedExternalDict

from nti.environments.management.dns import is_dns_name_available as _is_dns_name_available

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.models.utils import get_sites_folder

from nti.app.environments.views.base import BaseView
from nti.app.environments.views.utils import raise_json_error
from nti.app.environments.auth import is_admin_or_account_manager


def is_dns_name_available(dns_name, sites_folder=None):
    """
    A domain is available if a) there are know sites that use the domain
    and b) there isn't a dns reservation for it.
    """
    sites_folder = get_sites_folder() if sites_folder is None else sites_folder
    for site in sites_folder.values():
        if dns_name in site.dns_names or ():
            return False
    return _is_dns_name_available(dns_name)


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

        # Expect all dns names should be lower case.
        # and ends with 'nextthought.io'
        dns_name = dns_name.lower()

        # Skip checking for admin and management roles.
        if not is_admin_or_account_manager(userid, self.request):
            if not dns_name.endswith('nextthought.io'):
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
