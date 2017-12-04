from setuptools import setup

setup(
    name='lektor-current-date',
    version='0.1',
    author=u'Wojtek Porczyk',
    author_email='w.porczyk@warszawa.oaza.pl',
    license='AGPLv3+',
    py_modules=['lektor_current_date'],
    entry_points={
        'lektor.plugins': [
            'current-date = lektor_current_date:CurrentDatePlugin',
        ]
    }
)
