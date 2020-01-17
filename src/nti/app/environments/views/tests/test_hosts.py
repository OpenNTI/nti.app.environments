from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import is_

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app


class TestHosts(BaseAppTest):

    @with_test_app()
    def testHostsViews(self):
        url = '/onboarding/hosts'
        params = {'host_name': 'okc', 'capacity': 10, 'MimeType': 'application/vnd.nextthought.app.environments.host'}
        self.testapp.post_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.post_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc',
                                         'capacity': 10,
                                         'current_load': 0}))

        result = self.testapp.post_json(url, params=params, status=409, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': "Existing host: okc."}))

        params = {'host_name': 'okc2', 'capacity': "ddd", 'MimeType': 'application/vnd.nextthought.app.environments.host'}
        result = self.testapp.post_json(url, params=params, status=422, extra_environ=self._make_environ(username='admin001'))
        assert_that(result.json_body, has_entries({'message': "invalid literal for int() with base 10: 'ddd'"}))

        params = {'host_name': 'okc2', 'capacity': 20, 'MimeType': 'application/vnd.nextthought.app.environments.host'}
        result = self.testapp.post_json(url, params=params, status=201, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc2',
                                         'capacity': 20,
                                         'current_load': 0}))
        host_id2 = result['id']

        # update
        url = '/onboarding/hosts/%s' % host_id2
        params = {'host_name': 'okc3', 'capacity': 30}
        self.testapp.put_json(url, params=params, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.put_json(url, params=params, status=403, extra_environ=self._make_environ(username='user001'))
        result = self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc3',
                                         'capacity': 30,
                                         'current_load': 0}))

        params = {'host_name': 'okc3', 'capacity': 30}
        result = self.testapp.put_json(url, params=params, status=200, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result, has_entries({'host_name': 'okc3',
                                         'capacity': 30,
                                         'current_load': 0}))

        params = {'host_name': 'okc', 'capacity': 30}
        result = self.testapp.put_json(url, params=params, status=409, extra_environ=self._make_environ(username='admin001')).json_body
        assert_that(result['message'], is_('Existing host: okc.'))

        # delete
        self.testapp.delete(url, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.delete(url, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.delete(url, status=204, extra_environ=self._make_environ(username='admin001'))

    @with_test_app()
    def testHostsListView(self):
        url = '/onboarding/hosts/@@list'
        self.testapp.get(url, status=302, extra_environ=self._make_environ(username=None))
        self.testapp.get(url, status=403, extra_environ=self._make_environ(username='user001'))
        self.testapp.get(url, status=200, extra_environ=self._make_environ(username='admin001'))
