from hamcrest import assert_that
from hamcrest import has_properties
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import calling
from hamcrest import raises
from hamcrest import is_

from zope.container.interfaces import InvalidItemType


from nti.externalization import to_external_object
from nti.externalization import update_from_external_object

from nti.app.environments.tests import BaseTest

from nti.app.environments.models.hosts import PersistentHost
from nti.app.environments.models.hosts import HostsFolder


class TestCustomers(BaseTest):

    def testPersistentHost(self):
        inst = PersistentHost(host_name='xxx', capacity=5)
        result = to_external_object(inst)
        assert_that(result, has_entries({'Class': 'PersistentHost',
                                         'MimeType': 'application/vnd.nextthought.app.environments.host',
                                         'host_name': 'xxx',
                                         'capacity': 5,
                                         'current_load': 0}))

        inst = update_from_external_object(inst, {'host_name': 'yyy', 'capacity': 6, 'current_load': 8, 'id': 'mock'})
        assert_that(inst, has_properties({'host_name': 'yyy', 'capacity': 6, 'current_load': 0, 'id': None}))

    def testHostsFolder(self):
        folder = HostsFolder()
        inst = PersistentHost(host_name='xxx', capacity=5)
        folder.addHost(inst)

        assert_that(folder, has_length(1))
        assert_that(folder[inst.id], is_(inst))

        assert_that(folder.getHost('yyy'), is_(None))
        assert_that(folder.getHost(inst.id), is_(inst))

        assert_that(calling(folder.__setitem__).with_args("okc", HostsFolder()), raises(InvalidItemType))

        folder.deleteHost(inst.id)
        assert_that(calling(folder.deleteHost).with_args(inst.id), raises(KeyError))
        assert_that(folder, has_length(0))
