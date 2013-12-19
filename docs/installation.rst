============
Installation
============

At the command line::

    $ easy_install django-mantis-iodef-importer

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv django-mantis-iodef-importer
    $ pip install django-mantis-iodef-importer

Once this is done, you can include 'mantis_iodef_importer' as app in your Django settings,
together with the apps ``dingos`` and ``mantis_core`` on which ``mantis_iodef_importer`` depends::

    INSTALLED_APPS_list = [
                           ...,
                           'dingos',
                           'mantis_core',
                           'mantis_iodef_importer',
                           ]

