#!/usr/bin/env python

from setuptools import setup

import versioneer
from _datalad_buildsupport.setup import BuildManPage

cmdclass = versioneer.get_cmdclass()
cmdclass.update(build_manpage=BuildManPage)

if __name__ == '__main__':
    setup(name='datalad_container',
          version=versioneer.get_version(),
          cmdclass=cmdclass,
    )
