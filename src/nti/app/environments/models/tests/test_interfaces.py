from hamcrest import is_
from hamcrest import calling
from hamcrest import raises
from hamcrest import assert_that

from nti.app.environments.models.interfaces import checkEmailAddress
from nti.app.environments.models.interfaces import checkRealname

from nti.app.environments.tests import BaseTest


class TestInterfaces(BaseTest):

    def testCheckEmailAddress(self):
        assert_that(checkEmailAddress(None), is_(False))
        assert_that(checkEmailAddress(''), is_(False))
        assert_that(checkEmailAddress('xxxx'), is_(False))
        assert_that(checkEmailAddress('xxxx@gmail.com'), is_(True))

    def testCheckRealname(self):
        assert_that(checkRealname(None), is_(True))
        assert_that(checkRealname(''), is_(True))
        assert_that(checkRealname('xxx xxx xxx'), is_(True))
        assert_that(checkRealname('xxxzz'), is_(True))
        
        assert_that(calling(checkRealname).with_args('333 333'), raises(ValueError))
        assert_that(calling(checkRealname).with_args('    '), raises(ValueError))
