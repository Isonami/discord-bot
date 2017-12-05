from setuptools import setup
import re

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

version = ''
with open('isobot/__init__.py') as f:
    version_str = 'from collections import namedtuple\n'
    version_str += re.search(r'^VersionInfo\s*=\s*namedtuple\s*\([^(]+\)\s*'
                             r'version_info\s*=\s*VersionInfo\s*\([^(]+\)\s*', f.read(), re.MULTILINE).group(0)
    version_str += 'version = \'{}.{}.{}\'.format(version_info.major, version_info.minor, version_info.micro)'
    exec(version_str)

if not version:
    raise RuntimeError('version is not set')

setup(name='isobot',
      author='Isonami',
      url='https://github.com/Isonami/discord-bot',
      version=version,
      packages=['isobot'],
      license='MIT',
      )
