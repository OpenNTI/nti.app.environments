#!/usr/bin/env python
# -*- coding: utf-8 -*-

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_in
from hamcrest import only_contains

import unittest

from ..authentication import EmailChallengeOTPGenerator
from ..authentication import _Z_BASE_32_ALPHABET

class TestEmailChallengeGeneratorTest(unittest.TestCase):

    def setUp(self):
        self.generator = EmailChallengeOTPGenerator()

    def test_generated_code(self):
        otp = self.generator.generate_passphrase()

        # By default we get a 12 character code
        assert_that(otp, has_length(12))

        # It's in z-base-32 alphabet
        assert_that(otp, only_contains(is_in(_Z_BASE_32_ALPHABET)))

        # We can ask for a longer code if we want
        assert_that(self.generator.generate_passphrase(100), has_length(100))
