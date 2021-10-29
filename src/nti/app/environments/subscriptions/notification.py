from zope import component

from zope.cachedescriptors.property import Lazy

from nti.app.environments.interfaces import IOnboardingSettings

from nti.environments.management.interfaces import ISettings

from nti.app.environments.notification import BaseEmailNotifier


class SubscriptionUpcomingInvoiceInternalNotifier(BaseEmailNotifier):

    _template = 'nti.app.environments:subscriptions/email_templates/upcoming_renewal_invoice_internal'

    _subject_prefix = 'Upcoming renewal charge'

    def __init__(self, site, request=None, invoice=None):
        super(SubscriptionUpcomingInvoiceInternalNotifier, self).__init__(site, request)
        self.site = site

    @Lazy
    def _subject(self):
        result = '%s [%s]' % (self._subject_prefix, self.site.id)
        settings = component.getUtility(ISettings)
        try:
            env_name = settings['general']['env_name']
        except KeyError:
            pass
        else:
            if env_name:
                result = '[%s] %s' % (env_name, result)
        return result

    def _recipients(self):
        settings = component.getUtility(IOnboardingSettings)
        setting = settings.get('internal_subscription_notification_recipients', '')
        return setting.split(',') if setting else []


    def _template_args(self):
        template_args = {
            'site_details_link': self.request.resource_url(self.site, '@@details'),
            'site_id': self.site.id,
            'dns_names': ','.join(self.site.dns_names),
            'owner_email': self.site.owner.email,
            'client_name': self.site.client_name,
        }
        return template_args

class SubscriptionStatusUpdatedNotifier(SubscriptionUpcomingInvoiceInternalNotifier):

    _template = 'nti.app.environments:subscriptions/email_templates/subscription_status_changed'

    @Lazy
    def _subject_prefix(self):
        return 'Subscription %s' % self.subscription.status

    def __init__(self, site, subscription, request=None):
        super(SubscriptionStatusUpdatedNotifier, self).__init__(site, request=request)
        self.subscription = subscription

    def _template_args(self):
        _args = super(SubscriptionStatusUpdatedNotifier, self)._template_args()
        _args['subscription_status'] = self.subscription.status
        return _args
