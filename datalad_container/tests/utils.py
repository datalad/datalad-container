import os
import os.path as op

from datalad.utils import chpwd
from datalad.tests.utils import SkipTest
from datalad.interface.common_cfg import dirs as appdirs


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
