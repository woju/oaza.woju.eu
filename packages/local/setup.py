from setuptools import setup

setup(
    name='lektor-local',
    version='0.1',
    author=u'Wojtek Porczyk',
    author_email='w.porczyk@warszawa.oaza.pl',
    license='AGPLv3+',
    py_modules=['lektor_local'],
    entry_points={
        'lektor.plugins': [
            'local = lektor_local:LocalPlugin',
        ]
    }
)
