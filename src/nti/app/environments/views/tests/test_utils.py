import datetime
import requests
import jwt

from unittest import mock

from hamcrest import is_
from hamcrest import calling
from hamcrest import raises
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import has_entries

from pyramid import exceptions as hexc

from zope import component

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import SchemaNotProvided
from zope.schema._bootstrapinterfaces import ValidationError
from zope.schema._bootstrapinterfaces import WrongContainedType

from nti.app.environments.api.siteinfo import NTClient
from nti.app.environments.api.siteinfo import query_invitation_status

from nti.app.environments.tasks.setup import query_setup_async_result

from nti.app.environments.views.utils import raise_json_error

from nti.environments.management.tasks import SiteInfo

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.models.interfaces import SITE_STATUS_ACTIVE
from nti.app.environments.models.interfaces import SITE_STATUS_INACTIVE

from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import SetupStateSuccess
from nti.app.environments.models.sites import SetupStatePending

from nti.app.environments.interfaces import IOnboardingSettings

from nti.app.environments.views.tests import BaseAppTest
from nti.app.environments.views.tests import with_test_app


class TestUtils(BaseAppTest):

    def test_raise_json_error(self):
        assert_that(calling(raise_json_error).with_args(hexc.HTTPBadRequest, "okc"),
                    raises(hexc.HTTPBadRequest, pattern="ok."))
        assert_that(calling(raise_json_error).with_args(hexc.HTTPBadRequest, "okc", field="name"),
                    raises(hexc.HTTPBadRequest, pattern="okc"))

        err = ConstraintNotSatisfied()
        err.args = ("test","xyz")
        assert_that(calling(raise_json_error).with_args(hexc.HTTPBadRequest, err, field="name"),
                    raises(hexc.HTTPBadRequest, pattern="Invalid xyz."))

        class _testclass(object): pass
        err = SchemaNotProvided(_testclass, 'test')
        assert_that(calling(raise_json_error).with_args(hexc.HTTPBadRequest, err, field="name"),
                    raises(hexc.HTTPBadRequest, pattern="test"))

        err = WrongContainedType()
        err.args = ((RequiredMissing(),), "age")
        assert_that(calling(raise_json_error).with_args(hexc.HTTPBadRequest, err, field="name"),
                    raises(hexc.HTTPBadRequest, pattern="Missing age."))

        assert_that(calling(raise_json_error).with_args(hexc.HTTPBadRequest, ValidationError()),
                    raises(hexc.HTTPBadRequest, pattern=""))

    @with_test_app()
    @mock.patch('nti.environments.management.tasks.SetupEnvironmentTask.restore_task')
    def test_query_setup_async_result(self, mock_restore_task):
        with mock.patch('nti.app.environments.models.utils.get_onboarding_root') as mock_get_onboarding_root:
            mock_get_onboarding_root.return_value = self._root()
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='user001@example.com', name="testname"))
            sites = self._root().get('sites')
            for email, siteId in (('user001@example.com', 'S001'),):
                sites.addSite(PersistentSite(dns_names=['xx.nextthought.io'],
                                             owner = customers.getCustomer(email),
                                             license=TrialLicense(start_date=datetime.datetime(2020, 1, 28),
                                                                  end_date=datetime.datetime(2020, 1, 9))), siteId=siteId)

        site = sites['S001']

        assert_that(site.setup_state, is_(None))
        assert_that(query_setup_async_result(site), is_(None))

        site.setup_state = SetupStatePending(task_state='ok')

        # mock async result
        mock_restore_task.return_value = async_result = mock.MagicMock(result="success")
        async_result.ready.return_value = None
        assert_that(query_setup_async_result(site), is_(None))

        async_result.ready.return_value = True
        assert_that(query_setup_async_result(site), is_('success'))

        site.setup_state = SetupStateSuccess(task_state='ok', site_info=SiteInfo(site_id='S001', dns_name='xx.nextthought.io'))
        assert_that(query_setup_async_result(site), is_(None))

    @mock.patch('nti.app.environments.api.siteinfo.requests.Session.get')
    def test_fetch_site_invitation(self, mock_get):
        settings = {}
        component.getGlobalSiteManager().registerUtility(settings, IOnboardingSettings)
        _result = []
        def _mock_get(url, params):
            _result.append((url, params))
            return {"acceptedTime": 30}

        site = PersistentSite()
        site.dns_names = ['demo.dev']

        nt_client = NTClient(site)
        
        mock_get.side_effect = _mock_get
        assert_that(nt_client.fetch_site_invitation('testcode'), is_({"acceptedTime": 30}))
        assert_that(_result[0][0], is_('https://demo.dev/dataserver2/Invitations/testcode'))
        assert_that(_result[0][1], has_entries({'jwt':not_none()}))
        decoded = jwt.decode(_result[0][1]['jwt'], '$Id$')
        assert_that(decoded, has_entries({'login': 'admin@nextthought.com',
                                         'realname': None,
                                         'email': None,
                                         'create': "true",
                                         "admin": "true",
                                         "iss": None}))

        mock_get.side_effect = requests.exceptions.ConnectionError
        assert_that(nt_client.fetch_site_invitation('testcode'), is_(None))

        component.getGlobalSiteManager().unregisterUtility(settings, IOnboardingSettings)

    @with_test_app()
    @mock.patch("nti.app.environments.api.siteinfo.NTClient.fetch_site_invitation")
    def test_query_invitation_status(self, mock_fetch):
        with mock.patch('nti.app.environments.models.utils.get_onboarding_root') as mock_onboarding_root:
            mock_onboarding_root.return_value = self._root()
            customers = self._root().get('customers')
            customers.addCustomer(PersistentCustomer(email='user001@example.com', name="testname"))
            sites = self._root().get('sites')
            for email, siteId in (('user001@example.com', 'S001'),
                                  ('user001@example.com', 'S002'),
                                  ('user001@example.com', 'S003'),
                                  ('user001@example.com', 'S004')):
                sites.addSite(PersistentSite(dns_names=[siteId],
                                             owner = customers.getCustomer(email),
                                             license=TrialLicense(start_date=datetime.datetime(2020, 1, 28),
                                                                  end_date=datetime.datetime(2020, 1, 9))), siteId=siteId)
                sites[siteId].status = SITE_STATUS_ACTIVE

            sites['S004'].status = SITE_STATUS_INACTIVE
            
        site = sites['S001']

        # state is not success
        site.setup_state = SetupStatePending(task_state='ok')
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 0}))

        site.setup_state = SetupStateSuccess(task_state='ok',
                                             invitation_active = False,
                                             site_info=SiteInfo(site_id='S001',
                                                                dns_name='xx.nextthought.io'))
        site.setup_state.site_info.task_result_dict = {'admin_invitation_code': 'testcode'}

        # invitation_active is not True
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 0}))

        # invite_accepted_date is not None
        site.setup_state.invitation_effecitve = True
        site.setup_state.invite_accepted_date = datetime.datetime(2020, 1, 26)
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 0}))

        # admin_invitation_code is None
        site.setup_state.invite_accepted_date = None
        site.setup_state.site_info.task_result_dict = {'admin_invitation_code': None}
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 0}))

        # okay, response is None
        mock_fetch.return_value = None
        site.setup_state.invitation_active = True
        site.setup_state.invite_accepted_date = None
        site.setup_state.site_info.task_result_dict = {'admin_invitation_code': 'testcode'}
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'unknown': 1}))

        # code is cancelled
        mock_fetch.return_value = mock.MagicMock(status_code=404)
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'cancelled': 1}))
        assert_that(site.setup_state.invitation_active, is_(False))
        assert_that(site.setup_state.invite_accepted_date, is_(None))
        assert_that(query_invitation_status([site]), has_entries({'total': 0}))

        # reset
        site.setup_state.invitation_active = True

        # bad authenticate
        mock_fetch.return_value = mock.MagicMock(status_code=401)
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'unknown': 1}))

        # good, haven't accepted
        mock_fetch.return_value = mock.MagicMock(status_code=200, json=lambda : {'acceptedTime': None,
                                                                                 'expiryTime': 0})
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'pending': 1}))

        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'pending': 1}))

        # accepted
        mock_fetch.return_value = mock.MagicMock(status_code=200, json=lambda : {'acceptedTime': 90,
                                                                                 'expiryTime': 1})

        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'accepted': 1}))
        assert_that(site.setup_state.invite_accepted_date, is_(datetime.datetime.utcfromtimestamp(90)))

        assert_that(query_invitation_status([site]), has_entries({'total': 0}))

        #reset
        site.setup_state.invite_accepted_date = None

        # expires
        mock_fetch.return_value = mock.MagicMock(status_code=200, json=lambda : {'acceptedTime': None,
                                                                                 'expiryTime': 1})
        result = query_invitation_status([site])
        assert_that(result, has_entries({'total': 1, 'expired': 1}))
        assert_that(site.setup_state.invitation_active, is_(False))
        assert_that(site.setup_state.invite_accepted_date, is_(None))

        assert_that(query_invitation_status([site]), has_entries({'total': 0}))

        # test many
        for site_id in ('S002', 'S003'):
            site = sites[site_id]
            site.setup_state = SetupStateSuccess(task_state='ok',
                                                 invitation_active = True,
                                                 site_info=SiteInfo(site_id=site_id,
                                                                    dns_name=site_id))
            site.setup_state.site_info.task_result_dict = {'admin_invitation_code': 'testcode'}

        mock_body = {'S002': mock.MagicMock(status_code=200, json=lambda : {'acceptedTime': 90,
                                                                            'expiryTime': 1}),
                     'S003': mock.MagicMock(status_code=200, json=lambda : {'acceptedTime': None,
                                                                                 'expiryTime': 1})
                                                                            }
        mock_fetch.side_effect = [mock_body['S002'], mock_body['S003']]
        assert_that(query_invitation_status([sites['S002'], sites['S003']]),
                    has_entries({'total': 2, 'accepted': 1, 'expired': 1}))
