from unittest import mock

from hamcrest import is_
from hamcrest import not_
from hamcrest import starts_with
from hamcrest import has_items
from hamcrest import has_length
from hamcrest import has_entries
from hamcrest import assert_that
from hamcrest import has_properties


from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.views.customers import EmailChallengeView

from nti.app.environments.views.tests import BaseAppTest, ensure_free_txn
from nti.app.environments.views.tests import with_test_app


class TestChallengeView(BaseAppTest):

    @with_test_app()
    def testChallengeView(self):
        customers = self._root().get('customers')
        view = EmailChallengeView(customers, self.request)
        assert_that(view._mailer(), not_(None))

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.EmailChallengeView._mailer')
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
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Invalid email.'}))

        params = {'name': '123456', 'email': 'test@example.com'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Invalid Realname 123456'}))

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

    @with_test_app()
    @mock.patch('nti.app.environments.views.customers.EmailChallengeView._mailer')
    def test_recovery_challenge(self, mock_mailer):
        # return a map of name, email, code_prefix.
        _result = []
        _mailer = mock.MagicMock()
        _mailer.queue_simple_html_text_email = lambda *args, **kwargs: _result.append((args, kwargs))
        mock_mailer.return_value = _mailer

        url = '/onboarding/customers/@@recovery_challenge'
        params = {}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Missing required field: email.'}))

        params = {'email': 'invalidemail'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'message': 'Invalid email.'}))

        params = {'email': 'test@example.com'}
        self.testapp.post_json(url, params=params, status=204, extra_environ=self._make_environ(username=None))

        assert_that(_result, has_length(1))
        assert_that(_result[0][0], is_(('nti.app.environments:email_templates/customer_not_found',)))
        assert_that(_result[0][1], has_entries({'subject': 'Your account is not found: test@example.com',
                                                'recipients': ['test@example.com'],
                                                'template_args': has_entries({'email': 'test@example.com', 'app_link': 'http://localhost'}),
                                                'text_template_extension': '.mak'}))
        _result.clear()

        with ensure_free_txn():
            customers = self._root().get('customers')
            assert_that(customers, has_length(0))
            customers.addCustomer(PersistentCustomer(email='test@example.com', name="Test User"))

        params = {'email': 'test@example.com'}
        self.testapp.post_json(url, params=params, status=204, extra_environ=self._make_environ(username=None))


        assert_that(customers['test@example.com'], has_properties({'email': 'test@example.com'}))
        assert_that(_result[0][0], is_(('nti.app.environments:email_templates/verify_recovery',)))
        assert_that(_result[0][1], has_entries({'subject': starts_with('Welcome back to NextThought!'),
                                                'recipients': ['test@example.com'],
                                                'template_args': has_entries({'name': 'Test User',
                                                                              'email': 'test@example.com',
                                                                              'code_suffix': has_length(6)}),
                                                'text_template_extension': '.mak'}))
        assert_that(_result[0][1]['template_args'].keys(), not_(has_items('url')))


class TestChallengerVerification(BaseAppTest):

    @with_test_app()
    @mock.patch('nti.app.environments.views.subscribers.get_hubspot_client')
    @mock.patch('nti.app.environments.views.customers.validate_challenge_for_customer')
    def test_email_challenge_verify(self, mock_validate, mock_client):
        url = '/onboarding/customers/@@email_challenge_verify'
        params = {}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: email.'))

        params = {'email': 'test@g.com'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: code.'))

        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_(u'This link is no longer valid. Please enter your email again.'))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='test@g.com'))

        mock_validate.return_value = False
        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_("That code wasn't valid. Give it another go!"))

        mock_validate.return_value = True
        mock_client.return_value = _client = mock.MagicMock()
        _client.upsert_contact = lambda email, name: {'contact_vid': '123'}

        params = {'email': 'test@g.com', 'code': 'xxxxxx', 'name': "okc"}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'email': 'test@g.com',
                                         'customer': has_entries({'email': 'test@g.com',
                                                                  'hubspot_contact': has_entries({'contact_vid': '123'})})}))

    @with_test_app()
    @mock.patch('nti.app.environments.views.subscribers.get_hubspot_client')
    @mock.patch('nti.app.environments.views.customers.validate_challenge_for_customer')
    def test_recovery_challenge_verify(self, mock_validate, mock_client):
        url = '/onboarding/customers/@@recovery_challenge_verify'
        params = {}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: email.'))

        params = {'email': 'test@g.com'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: code.'))

        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_(u'This link is no longer valid. Please enter your email again.'))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='test@g.com'))

        mock_validate.return_value = False
        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.post_json(url, params=params, status=400, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_("That code wasn't valid. Give it another go!"))

        mock_validate.return_value = True
        mock_client.return_value = _client = mock.MagicMock()
        _client.upsert_contact = lambda email, name: {'contact_vid': '123'}

        params = {'email': 'test@g.com', 'code': 'xxxxxx', 'name': "okc"}
        result = self.testapp.post_json(url, params=params, status=200, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result, has_entries({'email': 'test@g.com',
                                         'customer': has_entries({'email': 'test@g.com',
                                                                  'hubspot_contact': has_entries({'contact_vid': '123'})})}))

    @with_test_app()
    @mock.patch('nti.app.environments.views.subscribers.get_hubspot_client')
    @mock.patch('nti.app.environments.views.customers.validate_challenge_for_customer')
    def test_recovery_challenge_verify_from_link(self, mock_validate, mock_client):
        url = '/onboarding/customers/@@recovery_challenge_verify'
        params = {}
        result = self.testapp.get(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: email.'))

        params = {'email': 'test@g.com'}
        result = self.testapp.get(url, params=params, status=422, extra_environ=self._make_environ(username=None)).json_body
        assert_that(result['message'], is_('Missing required field: code.'))

        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        assert_that(result.location,
                    is_("http://localhost/recover?error=This%20link%20is%20no%20longer%20valid.%20Please%20enter%20your%20email%20again."))

        with ensure_free_txn():
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='test@g.com'))

        mock_validate.return_value = False
        params = {'email': 'test@g.com', 'code': 'xxxxxx'}
        result = self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        assert_that(result.location,
                    is_("http://localhost/recover?error=This%20link%20is%20no%20longer%20valid.%20Please%20enter%20your%20email%20again."))

        mock_validate.return_value = True
        mock_client.return_value = _client = mock.MagicMock()
        _client.upsert_contact = lambda email, name: {'contact_vid': '123'}

        params = {'email': 'test@g.com', 'code': 'xxxxxx', 'name': "okc"}
        result = self.testapp.get(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        assert_that(result.location, is_('http://localhost'))
        assert_that(customers['test@g.com'].hubspot_contact, has_properties({'contact_vid': '123'}))


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
    @mock.patch('nti.app.environments.views.base.get_hubspot_client')
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
