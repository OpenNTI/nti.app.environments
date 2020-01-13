import unittest

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

class TestUtils(unittest.TestCase):

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
