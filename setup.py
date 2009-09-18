from setuptools import setup

setup(
    name = 'django-babelsearch',
    version = '0.1',
    packages = ['babelsearch'],
    author = 'Antti Kaihola',
    author_email = 'akaihol+django@ambitone.com',
    description = ('Indexing/search re-usable app for Django '
                   'featuring multi-language capabilities'),
    url = 'http://github.com/akaihola/django-babelsearch/tree/master',
    download_url = ('http://www.github.com/akaihola/django-babelsearch/'
                    'tarball/0.1'),
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development'),
    )
