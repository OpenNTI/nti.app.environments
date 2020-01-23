from pyramid.view import view_config

from nti.app.environments.models.interfaces import IOnboardingRoot

from nti.app.environments.models.utils import get_customers_folder

from nti.externalization.interfaces import LocatedExternalDict

from .base import BaseView


@view_config(renderer='rest',
             context=IOnboardingRoot,
             request_method='GET',
             name="session.ping")
class SessinoPingView(BaseView):

    def __call__(self):
        result = LocatedExternalDict()
        result.__name__ = self.context.__name__
        result.__parent__ = self.context.__parent__

        email = self.request.authenticated_userid
        if email:
            result['email'] = email
            customers = get_customers_folder(self.context, request=self.request)
            if email in customers:
                result['customer'] = customers.get(email)
        return result
