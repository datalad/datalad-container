#!/usr/bin/env python3
"""Procedure to configure dataset for containers
"""

import sys

from datalad.distribution.dataset import require_dataset
from datalad.support import path as op

ds = require_dataset(
    sys.argv[1],
    check_installed=True,
    purpose='Containers dataset configuration')

# unless taken care of by the template already, each item in here
# will get its own .gitattributes entry to keep it out of the annex
# give relative path to dataset root (use platform notation)
force_in_git = [
    op.join('environments','**','*.json'),
    op.join('environments','*','image','repositories'),
]
# make an attempt to discover the prospective change in .gitattributes
# to decide what needs to be done, and make this procedure idempotent
# (for simple cases)
attr_fpath = op.join(ds.path, '.datalad', '.gitattributes')
if op.lexists(attr_fpath):
    with open(attr_fpath, 'rb') as f:
        attrs = f.read().decode()
else:
    attrs = ''

# amend gitattributes, if needed
ds.repo.set_gitattributes([
    (path, {'annex.largefiles': 'nothing'})
    for path in force_in_git
    if '{} annex.largefiles=nothing'.format(path) not in attrs
], attrfile=attr_fpath)

# leave clean
ds.save(
    path=[attr_fpath],
    message="Apply default containers dataset setup",
    to_git=True,
)
