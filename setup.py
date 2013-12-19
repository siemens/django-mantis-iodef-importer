# -*- coding: utf-8 -*-
#!/usr/bin/env python

import os
import sys

import mantis_iodef_importer

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

version = mantis_iodef_importer.__version__

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    print("You probably want to also tag the version now:")
    print("  git tag -a %s -m 'v%s'" % (version, version))
    print("  git push origin --tags")
    print("  git push github --tags")
    sys.exit()

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='django-mantis-iodef-importer',
    version=version,
    description='A iodef importer for the  Mantis Cyber Threat Intelligence Mgmt. Framework.',
    long_description=readme + '\n\n' + history,
    author='Siemens',
    author_email='mantis.cert@siemens.com',
    url='https://github.com/siemens/django-mantis-iodef-importer',
    packages=[
        'mantis_iodef_importer',
    ],
    include_package_data=True,
    install_requires=[
        "django>=1.5.5",
        "django-dingos>=0.1.0",
        "django-mantis-core>=0.1.0"
    ],
    license="GPLv2+",
    zip_safe=False,
    keywords='django-mantis-iodef-importer',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Topic :: Security'
    ],
    test_suite = 'runtests.run_tests'
)
