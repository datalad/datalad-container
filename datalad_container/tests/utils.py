import os
import os.path as op
import sys

from datalad.api import containers_add
from datalad.utils import chpwd
from datalad.tests.utils_pytest import SkipTest
from datalad.interface.common_cfg import dirs as appdirs


def add_pyscript_image(ds, container_name, file_name):
    """Set up simple Python script as image.

    Parameters
    ----------
    ds : Dataset
    container_name : str
        Add container with this name.
    file_name : str
        Write script to this file and use it as the image.
    """
    ds_file = (ds.pathobj / file_name)
    ds_file.write_text("import sys\nprint(sys.argv)\n")
    ds.save(ds_file, message="Add dummy container")
    containers_add(container_name, image=str(ds_file),
                   call_fmt=sys.executable + " {img} {cmd}",
                   dataset=ds)


def get_singularity_image():
    imgname = 'datalad_container_singularity_testimg.simg'
    targetpath = op.join(
        appdirs.user_cache_dir,
        imgname)
    if op.exists(targetpath):
        return targetpath

    with chpwd(appdirs.user_cache_dir):
        os.system(
            'singularity pull --name "{}" shub://datalad/datalad-container:testhelper'.format(
                imgname))

    if op.exists(targetpath):
        return targetpath

    raise SkipTest
