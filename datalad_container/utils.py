import logging

lgr = logging.getLogger("datalad.containers.utils")


def ensure_datalad_remote(repo):
    """Initialize and enable datalad special remote if it isn't already."""
    dl_remote = None
    for info in repo.get_special_remotes().values():
        if info["externaltype"] == "datalad":
            dl_remote = info["name"]
            break

    if not dl_remote:
        from datalad.consts import DATALAD_SPECIAL_REMOTE
        from datalad.customremotes.base import init_datalad_remote

        init_datalad_remote(repo, DATALAD_SPECIAL_REMOTE, autoenable=True)
    elif repo.is_special_annex_remote(dl_remote, check_if_known=False):
        lgr.debug("datalad special remote '%s' is already enabled",
                  dl_remote)
    else:
        lgr.debug("datalad special remote '%s' found. Enabling",
                  dl_remote)
        repo.enable_remote(dl_remote)
