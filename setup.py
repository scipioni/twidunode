# -*- coding: utf-8 -*-

import os
import sys

from setuptools import find_packages, setup

requires = [
    'pyserial-asyncio',
    'sanic'
]

setup(name='twidunode',
      version='0.0.1',
      classifiers=[
          "Programming Language :: Python",
      ],
      author='Stefano Scipioni',
      author_email='stefano.scipioni@csgalileo.org',
      url='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      entry_points={
          'console_scripts': ['twidunode_run = twidunode.main:main'],
      },
      )
