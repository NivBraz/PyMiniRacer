#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pip
import sys
import codecs
import pkg_resources
import traceback

from itertools import chain
from subprocess import check_call, check_output, STDOUT
from os.path import dirname, abspath, join, isfile, isdir, basename

from distutils.file_util import copy_file

try:
    from setuptools import setup, Extension, Command
    from setuptools.command.build_ext import build_ext
    from setuptools.command.install import install
except ImportError:
    from distutils.core import setup, Extension, Command
    from distutils.command.build_ext import build_ext
    from distutils.command.install import install

from py_mini_racer import __version__
from py_mini_racer.extension.v8_build import build_v8, \
    local_path as local_path_v8


with codecs.open('README.rst', 'r', encoding='utf8') as readme_file:
    readme = readme_file.read()

    # Convert local image links by their github equivalent
    readme = readme.replace(".. image:: data/",
                            ".. image:: https://github.com/sqreen/PyMiniRacer/raw/master/data/")

with codecs.open('HISTORY.rst', 'r', encoding='utf8') as history_file:
    history = history_file.read().replace('.. :changelog:', '')


def _parse_requirements(filepath):
    pip_version = list(map(int, pkg_resources.get_distribution('pip').version.split('.')[:2]))
    if pip_version >= [10, 0]:
        from pip._internal.download import PipSession
        from pip._internal.req import parse_requirements
        raw = parse_requirements(filepath, session=PipSession())
    elif pip_version >= [6, 0]:
        from pip.download import PipSession
        from pip.req import parse_requirements
        raw = parse_requirements(filepath, session=PipSession())
    else:
        from pip.req import parse_requirements
        raw = parse_requirements(filepath)

    return [str(i.req) for i in raw]


requirements = _parse_requirements('requirements/prod.txt')
setup_requires = _parse_requirements('requirements/setup.txt')
test_requirements = _parse_requirements('requirements/test.txt')


def local_path(path):
    """ Return path relative to this file
    """
    current_path = dirname(__file__)
    return abspath(join(current_path, path))


def check_python_version():
    """ Check that the python executable is Python 2.7.
    """
    output = check_output(['python', '--version'], stderr=STDOUT)
    return output.strip().decode().startswith('Python 2.7')


def is_depot_tools_checkout():
    """ Check if the depot tools submodule has been checkouted
    """
    return isdir(local_path('vendor/depot_tools'))


def is_v8_built():
    """ Return True if V8 was already built
    """
    files = ["libv8_base.a"]
    return all([os.path.isfile(local_path_v8(os.path.join(
        "out", "obj", "v8", f))) for f in files])


class V8Extension(Extension):

    def __init__(self, dest_module, cmakelists_dir=".", target=None, options=None, sources=[], **kwa):
        Extension.__init__(self, dest_module, sources=sources, **kwa)
        self.cmakelists_dir = os.path.abspath(cmakelists_dir)
        self.target = target
        self.options = options


class MiniRacerBuildExt(build_ext):

    def get_filename(self):
        if os.name == "posix" and sys.platform == "darwin":
            prefix, ext = "lib", ".dylib"
        elif sys.platform == "win32":
            prefix, ext = "", ".dll"
        else:
            prefix, ext = "lib", ".so"
        return prefix + "mini_racer" + ext

    def get_ext_filename(self, name):
        ext = ".so"
        parts = name.split(".")
        last = parts.pop(-1) + ext
        return os.path.join(*(parts + [last]))

    def build_extensions(self):
        try:
            self.debug = True
            src = os.path.join(local_path_v8("out"), self.get_filename())
            dest = os.path.join(self.build_lib, self.get_ext_filename("_v8"))
            if not os.path.isfile(src):
                self.reinitialize_command("build_v8", target="py_mini_racer_shared_lib")
                self.run_command("build_v8")
            copy_file(src, dest)
        except Exception as e:
            traceback.print_exc()

            # Alter message
            err_msg = """py_mini_racer failed to build, ensure you have an up-to-date pip (>= 8.1) to use the wheel instead
            To update pip: 'pip install -U pip'
            See also: https://github.com/sqreen/PyMiniRacer#binary-builds-availability

            Original error: %s"""

            raise Exception(err_msg % repr(e))


PY_MINI_RACER_EXTENSION = V8Extension("py_mini_racer._v8")


class MiniRacerBuildV8(Command):

    description = 'Compile vendored v8'
    user_options = [
      # The format is (long option, short option, description).
      ('target=', None, 'Build this target (default is v8)'),
    ]

    def initialize_options(self):
        """Set default values for options."""
        self.target = None

    def finalize_options(self):
        """Post-process options."""
        pass

    def run(self):
        if (self.target is None or self.target == "v8") and is_v8_built():
            print("v8 was already built")
            return

        if not check_python_version():
            msg = """py_mini_racer cannot build V8 in the current configuration.
            The V8 build system requires the python executable to be Python 2.7.
            See also: https://github.com/sqreen/PyMiniRacer#build"""
            raise Exception(msg)

        if not is_depot_tools_checkout():
            print("cloning depot tools submodule")
            check_call(['git', 'clone', 'https://chromium.googlesource.com/chromium/tools/depot_tools.git', 'vendor/depot_tools'])

        print("building {}".format(self.target or "v8"))
        build_v8(self.target)


setup(
    name='py_mini_racer',
    version=__version__,
    description="Minimal, modern embedded V8 for Python.",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/markdown',
    author='Sqreen',
    author_email='hey@sqreen.io',
    url='https://github.com/sqreen/PyMiniRacer',
    packages=[
        'py_mini_racer',
        'py_mini_racer.extension'
    ],
    ext_modules=[PY_MINI_RACER_EXTENSION],
    package_dir={'py_mini_racer':
                 'py_mini_racer'},
    include_package_data=True,
    setup_requires=setup_requires,
    install_requires=requirements,
    license="ISCL",
    zip_safe=False,
    keywords='py_mini_racer',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    cmdclass={
        "build_ext": MiniRacerBuildExt,
        'build_v8': MiniRacerBuildV8,
    }
)
