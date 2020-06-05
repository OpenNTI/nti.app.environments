from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry

import fudge
from fudge.inspector import arg

from stripe.util import convert_to_stripe_object

from nti.app.environments.stripe.interfaces import IStripeCustomer

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app
from nti.app.environments.views.tests import ensure_free_txn

from nti.app.environments.models.customers import PersistentCustomer

class TestStripeCustomerView(BaseAppTest):

    @with_test_app()
    def test_link_stripe_customer(self):
        email = '123@gmail.com'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email=email,
                                                     name="testname"))

        url = f'/onboarding/customers/{email}/stripe_customer'

        # only admins should be able to update a stripe customer_id,
        # no one else, including the customer themselves can manipulate that
        self.testapp.put_json(url,
                              params={'customer_id': 'cus1234'},
                              status=403,
                              extra_environ=self._make_environ(username=email))

        resp = self.testapp.put_json(url,
                                     params={'customer_id': 'cus1234'},
                                     status=200,
                                     extra_environ=self._make_environ(username='admin001'))
        resp = resp.json_body
        assert_that(resp, has_entry('customer_id', 'cus1234'))

SESSION_EXAMPLE = {
    "id": "bps_1GkZmRJSl3QXdEfxVVbCVU3I",
    "object": "billing_portal.session",
    "created": 1589911387,
    "customer": "cus_HJCALoxCODL3uv",
    "livemode": True,
    "return_url": "https://example.com/account",
    "url": "https://billing.stripe.com/session/{SESSION_SECRET}"
}
        
class TestManageBillingView(BaseAppTest):

    @with_test_app()
    @fudge.patch('nti.app.environments.stripe.billing.StripeBillingPortal.generate_session')
    def test_manage_billing(self, mock_generate_session):
        email = '123@gmail.com'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customer = PersistentCustomer(email=email,
                                          name="testname")
            customers.addCustomer(customer)
            IStripeCustomer(customer).customer_id = 'cus_1234'

        url = f'/onboarding/customers/{email}/stripe_customer/@@manage_billing'

        # In this case only the customer can access this view
        self.testapp.post(url,
                          status=403,
                          extra_environ=self._make_environ(username='admin001'))

        mock_generate_session.expects_call().with_args(arg.has_attr(customer_id='cus_1234'),
                                                       arg.contains(email)).returns(convert_to_stripe_object(SESSION_EXAMPLE))

        resp = self.testapp.post(url,
                                 status=303,
                                 extra_environ=self._make_environ(username=email))


    @with_test_app()
    @fudge.patch('nti.app.environments.stripe.billing.StripeBillingPortal.generate_session')
    def test_manage_billing(self, mock_generate_session):
        email = '123@gmail.com'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customer = PersistentCustomer(email=email,
                                          name="testname")
            customers.addCustomer(customer)
            IStripeCustomer(customer).customer_id = 'cus_1234'

        url = f'/onboarding/customers/{email}/stripe_customer/@@manage_billing?return=https%3A%2F%2Fexample.com%2Freturn'

        mock_generate_session.expects_call().with_args(arg.has_attr(customer_id='cus_1234'),
                                                       'https://example.com/return').returns(convert_to_stripe_object(SESSION_EXAMPLE))

        resp = self.testapp.post(url,
                                 status=303,
                                 extra_environ=self._make_environ(username=email))    



