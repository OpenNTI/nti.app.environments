from unittest import mock

from hamcrest import is_
from hamcrest import not_
from hamcrest import calling
from hamcrest import raises
from hamcrest import starts_with
from hamcrest import has_items
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_properties

from pyramid import httpexceptions as hexc

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.views.customers import ChallengeView
from nti.app.environments.views.customers import EmailChallengeView
from nti.app.environments.views.customers import EmailChallengeVerifyView

from nti.app.environments.views.tests import BaseAppTest, ensure_free_txn
from nti.app.environments.views.tests import with_test_app


class TestChallengeView(BaseAppTest):

    @with_test_app()
    def testChallengeView(self):
        customers = self._root().get('customers')
        view = ChallengeView(customers, self.request)
        assert_that(view._mailer(), not_(None))

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.ChallengeView._mailer')
    def test_challenge_customer(self, mock_mailer):
        # return a redirect_uri link.
        _result = []
        _mailer = mock.MagicMock()
        _mailer.queue_simple_html_text_email = lambda *args, **kwargs: _result.append((args, kwargs))
        mock_mailer.return_value = _mailer

        url = '/onboarding/customers/@@challenge_customer'
        params = {}
        result = self.testapp.post(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Missing required field: name.'}))

        params = {'name': 'Test User'}
        result = self.testapp.post(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Missing required field: email.'}))

        params = {'name': 'Test User', 'email': 'invalidemail'}
        result = self.testapp.post(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Invalid email.'}))

        params = {'name': 'Test User', 'email': 'test@example.com'}
        result = self.testapp.post(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'redirect_uri': 'http://localhost/onboarding/customers/@@email_challenge_verify'}))

        customers = self._root().get('customers')
        assert_that(customers['test@example.com'], has_properties({'email': 'test@example.com'}))
        assert_that(_result[0][0], is_(('nti.app.environments:email_templates/verify_customer',)))
        assert_that(_result[0][1], has_entries({'subject': starts_with('NextThought Confirmation Code:'),
                                                'recipients': ['test@example.com'],
                                                'template_args': has_entries({'name': 'Test User',
                                                                              'email': 'test@example.com',
                                                                              'code_suffix': has_length(6),
                                                                              'url': starts_with('http://localhost/onboarding/customers/@@verify_challenge')}),
                                                'text_template_extension': '.mak'}))

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.ChallengeView._mailer')
    def test_email_challenge(self, mock_mailer):
        # return a map of name, email, code_prefix.
        _result = []
        _mailer = mock.MagicMock()
        _mailer.queue_simple_html_text_email = lambda *args, **kwargs: _result.append((args, kwargs))
        mock_mailer.return_value = _mailer

        url = '/onboarding/customers/@@email_challenge'
        params = {}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Missing required field: name.'}))

        params = {'name': 'Test User'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Missing required field: email.'}))

        params = {'name': 'Test User', 'email': 'invalidemail'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Invalid email.'}))

        params = {'name': 'Test User', 'email': 'test@example.com'}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'name': 'Test User',
                                         'email': 'test@example.com',
                                         'code_prefix': has_length(6)}))
        customers = self._root().get('customers')
        assert_that(customers['test@example.com'], has_properties({'email': 'test@example.com'}))
        assert_that(_result[0][0], is_(('nti.app.environments:email_templates/verify_customer',)))
        assert_that(_result[0][1], has_entries({'subject': starts_with('NextThought Confirmation Code: '),
                                                'recipients': ['test@example.com'],
                                                'template_args': has_entries({'name': 'Test User',
                                                                              'email': 'test@example.com',
                                                                              'code_suffix': has_length(6)}),
                                                'text_template_extension': '.mak'}))
        assert_that(_result[0][1]['template_args'].keys(), not_(has_items('url')))


class TestChallengerVerification(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.validate_challenge_for_customer')
    def test_verify_challenge(self, mock_validate):
        url = '/onboarding/customers/@@verify_challenge'
        params = {}
        result = self.testapp.post(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: email.'))

        params = {'email': 'test@g.com'}
        result = self.testapp.post(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: code.'))

        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Bad request.'))

        result = self.testapp.get(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Bad request.'))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='test@g.com'))

        mock_validate.return_value = False
        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_("That code wasn't valid. Give it another go!"))

        result = self.testapp.get(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_("That code wasn't valid. Give it another go!"))

        mock_validate.return_value = True
        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'redirect_uri': '/'}))

        result = self.testapp.get(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'redirect_uri': '/'}))

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.validate_challenge_for_customer')
    def test_email_challenge_verify(self, mock_validate):
        url = '/onboarding/customers/@@email_challenge_verify'
        params = {}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: email.'))

        params = {'email': 'test@g.com'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: code.'))

        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Bad request.'))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='test@g.com'))

        mock_validate.return_value = False
        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_("That code wasn't valid. Give it another go!"))

        mock_validate.return_value = True
        params = {'email': 'test@g.com', 'code': 'xxxxxx', 'name': "okc"}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'email': 'test@g.com',
                                         'customer': has_entries({'email': 'test@g.com'})}))


class TestChallegePages(BaseAppTest):

    @with_test_app()
    def testEmailChallengeView(self):
        customers = self._root().get('customers')
        view = EmailChallengeView(customers, self.request)
        assert_that(view(), has_entries({'url':'http://example.com/onboarding/customers/@@challenge_customer'}))

        url = '/onboarding/customers/@@email_challenge'
        self.testapp.get(url, params={}, status=200, extra_environ=self._make_environ(username=None))

    @with_test_app()
    def testEmailChallengeVerifyView(self):
        customers = self._root().get('customers')
        view = EmailChallengeVerifyView(customers, self.request)
        _mock_values = {'name': 'test', 'email': 't@g.com', 'code_prefix': 'xxxx'}
        view._get_flash_value = lambda name: _mock_values.get(name)

        assert_that(view(), has_entries({'name': 'test', 'email': 't@g.com', 'code_prefix': 'xxxx',
                                         'url':'http://example.com/onboarding/customers/@@verify_challenge'}))

        _mock_values = {'name': 'test', 'email': 't@g.com'}
        assert_that(calling(view), raises(hexc.HTTPFound))
        _mock_values = {'name': 'test', 'code': 'xxxx'}
        assert_that(calling(view), raises(hexc.HTTPFound))
        _mock_values = {'email': 't@g.com', 'code': 'xxxx'}
        assert_that(calling(view), raises(hexc.HTTPFound))

        url = '/onboarding/customers/@@email_challenge_verify'
        self.testapp.get(url, params={}, status=302, extra_environ=self._make_environ(username=None))

class TestCustomersViews(BaseAppTest):

    @with_test_app()
    def testCustomerListView(self):
        url = '/onboarding/customers'
        self.testapp.get(url, params={}, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, params={}, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.get(url, params={}, status=200, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_length(0))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='user001@example.com'))

        result = self.testapp.get(url, params={}, status=200, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_length(1))
        assert_that(result[0], has_entries({'email': 'user001@example.com',
                                            'MimeType': 'application/vnd.nextthought.app.environments.customer'}))

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.get_hubspot_client')
    def testCustomerCreationAndDeletion(self, mock_client):
        mock_client.return_value = _client = mock.MagicMock()
        _client.fetch_contact_by_email = lambda email: None

        customers = self._root().get('customers')
        assert_that(customers, has_length(0))

        url = '/onboarding/customers/@@hubspot'
        params = {}
        self.testapp.post(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.post(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post(url, params=params, status=400, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], is_('Missing required email'))

        params = {'email': 'xxx'}
        result = self.testapp.post(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], is_('Invalid email.'))

        params = {'email': 'test@ex.com'}
        result = self.testapp.post(url, params=params, status=422, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], is_('No hubspot contact found: test@ex.com.'))

        _client.fetch_contact_by_email = lambda email: {'canonical-vid': 123,
                                                        'email': email,
                                                        'name': 'Test User'}
        params = {'email': 'test@ex.com'}
        self.testapp.post(url, params=params, status=201, extra_environ=self._make_environ(username='admin001'))
        assert_that(customers, has_length(1))
        assert_that(customers['test@ex.com'], has_properties({'name': 'Test User', 'email': 'test@ex.com',
                                                              'hubspot_contact': has_properties({'contact_vid': '123'})}))

        params = {'email': 'test@ex.com'}
        result = self.testapp.post(url, params=params, status=409, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], is_('Existing customer: test@ex.com.'))

        # deletion
        url = '/onboarding/customers/test@ex.com'
        self.testapp.delete(url, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.delete(url, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.delete(url, status=204, extra_environ=self._make_environ(username='admin001'))
        assert_that(customers, has_length(0))
