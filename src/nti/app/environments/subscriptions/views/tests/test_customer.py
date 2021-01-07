from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import contains_string

import fudge
from fudge.inspector import arg

import json

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


SESSION_JSON = """{
  "id": "cs_test_LVpQ7aF5yIQILeZXUTV9o9IqLchDPCkfnENiVsR3YE3tIAPuy4qvdeHj",
  "object": "checkout.session",
  "allow_promotion_codes": null,
  "amount_subtotal": null,
  "amount_total": null,
  "billing_address_collection": null,
  "cancel_url": "https://example.com/cancel",
  "client_reference_id": null,
  "currency": null,
  "customer": null,
  "customer_email": null,
  "livemode": false,
  "locale": null,
  "metadata": {},
  "mode": "payment",
  "payment_intent": "pi_1GqiTLJSl3QXdEfxVFCgmpNl",
  "payment_method_types": [
    "card"
  ],
  "payment_status": "unpaid",
  "setup_intent": null,
  "shipping": null,
  "shipping_address_collection": null,
  "submit_type": null,
  "subscription": null,
  "success_url": "https://example.com/success",
  "total_details": null,
  "line_items": [
    {
      "price": "price_H5ggYwtDq4fbrJ",
      "quantity": 2
    }
  ]
}"""

SESSION_EXAMPLE = convert_to_stripe_object(json.loads(SESSION_JSON))
        
class TestManageBillingView(BaseAppTest):

    @with_test_app()
    @fudge.patch('nti.app.environments.stripe.checkout.StripeCheckout.generate_setup_session')
    def test_manage_billing(self, mock_setup_session):
        email = '123@gmail.com'
        with ensure_free_txn():
            customers = self._root().get('customers')
            customer = PersistentCustomer(email=email,
                                          name="testname")
            customers.addCustomer(customer)
            IStripeCustomer(customer).customer_id = 'cus_1234'

        url = f'/onboarding/customers/{email}/stripe_customer/@@manage_billing'
        return_url = f'http://localhost/onboarding/customers/{email}/@@details'

        # In this case only the customer can access this view
        self.testapp.get(url,
                         status=403,
                         extra_environ=self._make_environ(username='admin001'))

        mock_setup_session.expects_call().with_args(return_url,
                                                    return_url,
                                                    client_reference_id=arg.any(),
                                                    customer=arg.has_attr(customer_id='cus_1234')).returns(SESSION_EXAMPLE)

        resp = self.testapp.get(url,
                                status=200,
                                extra_environ=self._make_environ(username=email))

        assert_that(resp.text, contains_string('pk_test_gsyBVYVrN6NNdMDxj6rGX3hc'))
        assert_that(resp.text, contains_string(SESSION_EXAMPLE.id))




