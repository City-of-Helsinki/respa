# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='respa',
    version='0.0.0',
    packages=find_packages('.'),  # TODO: Probably not wise
    include_package_data=True,
    install_requires=[],  # TODO: See requirements.txt
    zip_safe=False,
)
