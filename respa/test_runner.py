# -*- coding: utf-8 -*-
import sys


class PyTestShimRunner(object):
    def __init__(self, **options):
        self.options = options

    def run_tests(self, test_labels, **kwargs):
        sys.stderr.write("***********************************************\n")
        sys.stderr.write("*** Please use `py.test` directly to run tests.\n")
        sys.stderr.write("***********************************************\n")
        import pytest
        pytest.main(" ".join(test_labels))
