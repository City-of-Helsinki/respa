# -*- coding: utf-8 -*-
import os
import re
from setuptools import setup, find_packages


def get_version(package):
    '''
    Return package version as listed in `__version__` in `respa/init.py`.
    '''
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.match("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


setup(
    name='respa',
    version=get_version('respa'),
    packages=find_packages('.'),  # TODO: Probably not wise
    include_package_data=True,
    install_requires=[],  # TODO: See requirements.txt
    zip_safe=False,
)
