from hamcrest import not_
from hamcrest import has_items
from hamcrest import has_entries
from hamcrest import assert_that

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.views.tests import BaseAppTest, ensure_free_txn
from nti.app.environments.views.tests import with_test_app


class TestSessinoPingView(BaseAppTest):

    @with_test_app()
    def test_session_ping(self):
        url = '/onboarding/session.ping'
        result = self.testapp.get(url, params={}, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result.keys(), not_(has_items('userid', 'customer')))
        result = self.testapp.get(url, params={}, status=200, extra_environ=self._make_environ(username='user001@example.com')).json_body
        assert_that(result, has_entries({'email': 'user001@example.com'}))
        assert_that(result.keys(), not_(has_items('customer')))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='user001@example.com'))

        result = self.testapp.get(url, params={}, status=200, extra_environ=self._make_environ(username='user001@example.com')).json_body
        assert_that(result, has_entries({'email': 'user001@example.com',
                                         'customer': has_entries({'email': 'user001@example.com',
                                                                  'MimeType': 'application/vnd.nextthought.app.environments.customer'})}))
