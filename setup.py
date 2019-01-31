import os
import re
import sys
from setuptools import setup, find_packages


if sys.version_info < (3, 5, 0):
    raise RuntimeError('sanic_zipkin does not support Python earlier than 3.5.0')


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()


install_requires = ['aiohttp>=3.0.0', 'aiozipkin>=0.5.0', 'Sanic-Plugins-Framework==0.6.5']
extras_require = {}


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*'([\d.abrc]+)'")
    init_py = os.path.join(os.path.dirname(__file__),
                           'sanic_zipkin', '__init__.py')
    with open(init_py) as f:
        for line in f:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        else:
            msg = 'Cannot find version in sanic_zipkin/__init__.py'
            raise RuntimeError(msg)


classifiers = [
    'License :: OSI Approved :: MIT License',
    'Intended Audience :: Developers',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Operating System :: POSIX',
]


setup(name='sanic-zipkin',
      version=read_version(),
      description=('Sanic plugin to use Distributed tracing instrumentation '
                   'for asyncio application with aiozipkin'),
      long_description='\n\n'.join((read('README.md'), read('CHANGES.txt'))),
      classifiers=classifiers,
      platforms=['POSIX'],
      author='Kevin ZHANG Qing',
      author_email='ezhqing@gmail.com',
      url='https://github.com/kevinqqnj/sanic-zipkin',
      download_url='https://pypi.python.org/pypi/sanic-zipkin',
      license='LICENSE.txt',
      packages=find_packages(),
      install_requires=install_requires,
      extras_require=extras_require,
      keywords=['sanic', 'sanic plugin', 'zipkin', 'distributed-tracing', 'tracing'],
      zip_safe=True,
      include_package_data=True)
