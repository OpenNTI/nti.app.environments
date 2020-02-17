import unittest
import datetime

from unittest import mock

from hamcrest import is_
from hamcrest import calling
from hamcrest import raises
from hamcrest import assert_that

from pyramid import exceptions as hexc

from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import SchemaNotProvided
from zope.schema._bootstrapinterfaces import ValidationError
from zope.schema._bootstrapinterfaces import WrongContainedType

from nti.app.environments.views.utils import raise_json_error
from nti.app.environments.views.utils import query_setup_async_result

from nti.environments.management.tasks import SiteInfo

from nti.app.environments.models.customers import PersistentCustomer

from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import SetupStateSuccess
from nti.app.environments.models.sites import SetupStatePending

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
                    raises(hexc.HTTPBadRequest, pattern="Missing field: age."))

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