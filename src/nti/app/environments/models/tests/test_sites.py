import datetime

from hamcrest import is_
from hamcrest import raises
from hamcrest import calling
from hamcrest import not_none
from hamcrest import has_items
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import assert_that
from hamcrest import starts_with

from zope.schema import getValidationErrors
from zope.schema._bootstrapinterfaces import RequiredMissing
from zope.schema._bootstrapinterfaces import ConstraintNotSatisfied

from nti.app.environments.models.sites import SharedEnvironment
from nti.app.environments.models.sites import DedicatedEnvironment
from nti.app.environments.models.sites import TrialLicense
from nti.app.environments.models.sites import EnterpriseLicense
from nti.app.environments.models.sites import PersistentSite
from nti.app.environments.models.sites import SitesFolder
from nti.app.environments.models.sites import _generate_site_id

from nti.app.environments.models.interfaces import ITrialLicense
from nti.app.environments.models.interfaces import IEnterpriseLicense
from nti.app.environments.models.interfaces import ISharedEnvironment
from nti.app.environments.models.interfaces import IDedicatedEnvironment
from nti.app.environments.models.interfaces import ILMSSite

from nti.app.environments.models.customers import PersistentCustomer
from nti.app.environments.models.customers import CustomersFolder

from nti.app.environments.tests import BaseTest


class TestSites(BaseTest):

    def testSharedEnvironment(self):
        inst = SharedEnvironment()
        assert_that(inst.name, is_(None))

        errors = getValidationErrors(ISharedEnvironment, inst)
        assert_that(errors, has_length(1))
        assert_that(errors, has_items(('name', RequiredMissing('name'))))

        inst = SharedEnvironment(name='alpha')
        assert_that(inst.name, is_('alpha'))
        errors = getValidationErrors(ISharedEnvironment, inst)
        assert_that(errors, has_length(0))

        assert_that(calling(SharedEnvironment).with_args(name='xxx'), raises(ConstraintNotSatisfied))

    def testDedicatedEnvironment(self):
        inst = DedicatedEnvironment()
        assert_that(inst, has_properties({'pod_id': None,
                                          'host': None}))
        errors = getValidationErrors(IDedicatedEnvironment, inst)
        assert_that(errors, has_length(2))
        assert_that(errors, has_items(('pod_id', RequiredMissing('pod_id')),
                                      ('host', RequiredMissing('host'))))

        inst = DedicatedEnvironment(pod_id='123456', host='sdsdfs')
        assert_that(inst, has_properties({'pod_id': '123456',
                                          'host': 'sdsdfs'}))
        errors = getValidationErrors(IDedicatedEnvironment, inst)
        assert_that(errors, has_length(0))

    def testTrialLicense(self):
        inst = TrialLicense()
        assert_that(inst, has_properties({'start_date': None,
                                          'end_date': None}))
        errors = getValidationErrors(ITrialLicense, inst)
        assert_that(errors, has_length(2))
        assert_that(errors, has_items(('start_date', RequiredMissing('start_date')),
                                      ('end_date', RequiredMissing('end_date'))))

        _start = datetime.datetime(2019, 12, 11, 0, 0, 0)
        _end = datetime.datetime(2019, 12, 12, 0, 0, 0)
        inst = TrialLicense(start_date=_start,
                            end_date=_end)
        assert_that(inst, has_properties({'start_date': _start,
                                          'end_date': _end}))
        errors = getValidationErrors(ITrialLicense, inst)
        assert_that(errors, has_length(0))

    def testEnterpriseLicense(self):
        inst = EnterpriseLicense()
        assert_that(inst, has_properties({'start_date': None,
                                          'end_date': None}))
        errors = getValidationErrors(IEnterpriseLicense, inst)
        assert_that(errors, has_length(2))
        assert_that(errors, has_items(('start_date', RequiredMissing('start_date')),
                                      ('end_date', RequiredMissing('end_date'))))

        _start = datetime.datetime(2019, 12, 11, 0, 0, 0)
        _end = datetime.datetime(2019, 12, 12, 0, 0, 0)
        inst = EnterpriseLicense(start_date=_start,
                            end_date=_end)
        assert_that(inst, has_properties({'start_date': _start,
                                          'end_date': _end}))
        errors = getValidationErrors(IEnterpriseLicense, inst)
        assert_that(errors, has_length(0))

    def testPersistentSite(self):
        inst = PersistentSite()
        assert_that(inst, has_properties({'id': None,
                                          'environment': None,
                                          'license': None,
                                          'owner': None,
                                          'owner_username': None,
                                          'created': None,
                                          'dns_names': (),
                                          'status': 'PENDING'}))
        errors = getValidationErrors(ILMSSite, inst)
        assert_that(errors, has_length(5))

        inst = PersistentSite(owner=PersistentCustomer(email='103@gmail.com', created=datetime.datetime.utcnow()))
        assert_that(inst.owner, is_(None))

        folder = CustomersFolder()
        owner = folder.addCustomer(PersistentCustomer(email='103@gmail.com', created=datetime.datetime.utcnow()))
        inst = PersistentSite(id='xxxxid',
                              owner=owner,
                              owner_username='test',
                              environment=SharedEnvironment(name='alpha'),
                              license=TrialLicense(start_date=datetime.datetime.utcnow(), end_date=datetime.datetime.utcnow()),
                              created=datetime.datetime.utcnow(),
                              dns_names=['t.nt.com'],
                              status='ACTIVE')
        assert_that(inst, has_properties({'id': 'xxxxid',
                                          'environment': not_none(),
                                          'license': not_none(),
                                          'owner': not_none(),
                                          'owner_username': 'test',
                                          'created': not_none(),
                                          'dns_names': ['t.nt.com'],
                                          'status': 'ACTIVE'}))
        errors = getValidationErrors(ILMSSite, inst)
        assert_that(errors, has_length(0))

    def testSitesFolder(self):
        folder = SitesFolder()
        site = PersistentSite(id='xxxxid',
                              owner=PersistentCustomer(email='103@gmail.com', created=datetime.datetime.utcnow()),
                              owner_username='test',
                              environment=SharedEnvironment(name='alpha'),
                              license=TrialLicense(start_date=datetime.datetime.utcnow(), end_date=datetime.datetime.utcnow()),
                              created=datetime.datetime.utcnow(),
                              dns_names=['t.nt.com'],
                              status='ACTIVE')
        folder.addSite(site, siteId='okc')
        assert_that(site.__name__, 'xxxxid')
        assert_that(folder, has_length(1))

        folder.deleteSite('xxxxid')
        assert_that(folder, has_length(0))

        site = PersistentSite()
        assert_that(site.__name__, is_(None))
        folder.addSite(site, siteId='abc')
        assert_that(site.__name__, is_('abc'))

        site = PersistentSite()
        assert_that(site.__name__, is_(None))
        folder.addSite(site)
        assert_that(site.__name__, not_none())
        assert_that(folder, has_length(2))

        site = PersistentSite()
        assert_that(calling(folder.addSite).with_args(site, siteId='abc'), raises(KeyError))
        assert_that(folder, has_length(2))

    def test_generate_site_id(self):
        _id = _generate_site_id()
        assert_that(_id, has_length(33))
        assert_that(_id, starts_with('S'))
