import sys
from setuptools import setup, find_packages


setup_dict = {
    'name': 'django-comments-xtd',
    'version': '2.0.0',
    'packages': find_packages(),
    'include_package_data': True,
    'license': 'MIT',
    'description': ("Django comments app with comment thread support, "
                    "follow up notifications, email confirmation and "
                    "Ajax support."),
    'long_description': ("A reusable Django app that extends django-contrib"
                         "-comments with comment threading, follow up "
                         "notifications, comments that only hits the database "
                         "when users confirm them by email and Ajax support."),
    'author': 'Daniel Rus Morales',
    'author_email': 'mbox@danir.us',
    'maintainer': 'Daniel Rus Morales',
    'maintainer_email': 'mbox@danir.us',
    'url': 'http://pypi.python.org/pypi/django-comments-xtd',
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Framework :: Django',
        'Natural Language :: English',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: News/Diary',
    ],
    'include_package_data': True,
    'install_requires': ['six',
                         'Django>=1.8',
                         'docutils',
                         'Markdown',
                         'django-markup']
}

setup(**setup_dict)
