"""Feed tagged Docker Hub images to datalad-containers-add.

This command takes a set of Docker Hub repositories, looks up the
tags, and calls `datalad containers-add ... dhub://REPO:TAG`.  The
output of datalad-container's Docker adapter is dumped to

    images/REPO/DIGEST/

where DIGEST is the .config.digest key of the manifest returned by
Docker Hub.  In addition, that manifest is written to
manifests/REPO/DIGEST.json.  In both cases, the step is skipped if the
path is already present locally.
"""

import fileinput
import json
import logging
from pathlib import Path
import re
import requests

lgr = logging.getLogger("containers_add_dhub_tags")

REGISTRY_AUTH_URL = ("https://auth.docker.io/token?service=registry.docker.io"
                     "&scope=repository:{repo}:pull")
REGISTRY_ENDPOINT = "https://registry-1.docker.io/v2"
DHUB_ENDPOINT = "https://hub.docker.com/v2"


def clean_container_name(name):
    """Transform `name` for use in datalad-containers-add.

    Note that, although it probably doesn't matter in practice, this
    transformation is susceptible to conflicts and ambiguity.
    """
    if name.startswith("library/"):
        name = name[8:]
    name = name.replace("_", "-")
    return re.sub(r"[^0-9a-zA-Z-]", "--", name)


def add_container(repo, tag, digest):
    from datalad.api import containers_add

    target = Path("images", repo, digest)
    if target.exists():
        lgr.info("Skipping %s:%s. Already exists: %s",
                 repo, tag, target)
        return

    name = clean_container_name(f"{repo}--{tag}")
    url = f"dhub://{repo}:{tag}"
    lgr.info("Adding %s as %s", url, name)
    # TODO: This would result in a commit for each image, which would
    # be good to avoid.
    #
    # This containers_add() call also prevents doing things in
    # parallel.
    containers_add(
        name=name, url=url, image=str(target),
        # Pass update=True to let the image for an existing entry
        # (particularly the one for the "latest" tag) be updated.
        update=True)


def write_manifest(repo, digest, manifest):
    target = Path(f"manifests/{repo}/{digest}.json")
    if target.exists():
        lgr.info("Manifest already exists: %s", target)
        return
    lgr.info("Writing %s", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest))


def get_manifests(repo, tags):
    resp_auth = requests.get(REGISTRY_AUTH_URL.format(repo=repo))
    resp_auth.raise_for_status()
    headers = {
        "Authorization": "Bearer " + resp_auth.json()["token"],
        "Accept": "application/vnd.docker.distribution.manifest.v2+json"}

    for tag in tags:
        lgr.debug("Getting manifest for %s:%s", repo, tag)
        # TODO: Can we check with HEAD first to see if the digest
        # matches what we have locally?
        resp_man = requests.get(f"{REGISTRY_ENDPOINT}/{repo}/manifests/{tag}",
                                headers=headers)
        resp_man.raise_for_status()
        yield tag, resp_man.json()


def walk_pages(url):
    next_page = url
    while next_page:
        lgr.debug("GET %s", next_page)
        response = requests.get(next_page)
        response.raise_for_status()
        data = response.json()
        next_page = data.get("next")
        yield from data.get("results", [])


def get_repo_tags(repo):
    url = f"{DHUB_ENDPOINT}/repositories/{repo}/tags"
    for result in walk_pages(url):
        yield result["name"]


def get_namespace_repos(name):
    lgr.info("Getting repositories for %s...", name)
    url = f"{DHUB_ENDPOINT}/repositories/{name}/"
    for result in walk_pages(url):
        assert name == result["namespace"]
        yield f"{name}/{result['name']}"


def parse_input(line):
    line = line.strip()
    lgr.debug("Processing input: %s", line)
    if line.endswith("/"):
        kind = "namespace"
        name = line[:-1]
    else:
        kind = "repository"
        if "/" in line:
            name = line
        else:
            lgr.debug(
                "Assuming official image and assigning library/ namespace")
            name = "library/" + line
    return name, kind


def process_files(files):
    failed = []
    for line in fileinput.input(files):
        name, kind = parse_input(line)
        if kind == "namespace":
            try:
                repos = list(get_namespace_repos(name))
            except requests.HTTPError as exc:
                lgr.warning(
                    "Failed to list repositories for %s (status %s). Skipping",
                    name, exc.response.status_code)
                failed.append(name)
                continue
        else:
            repos = [name]

        for repo in repos:
            try:
                for tag, manifest in get_manifests(repo, get_repo_tags(repo)):
                    digest = manifest["config"]["digest"]
                    assert digest.startswith("sha256:")
                    digest = digest[7:]
                    write_manifest(repo, digest, manifest)
                    add_container(repo, tag, digest)
            except requests.HTTPError as exc:
                lgr.warning(
                    "Failed processing %s. Skipping\n  status %s for %s",
                    repo, exc.response.status_code, exc.response.url)
                failed.append(name)
                continue
    return failed


def main(args):
    import argparse

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v", "--verbose", action="store_true")
    parser.add_argument(
        "files", metavar="FILE", nargs="*",
        help=("File with list of names. "
              "If a name doesn't contain a slash, "
              "it's treated as an official image by prepending 'library/'. "
              "A name ending with a slash is taken as a namespace, "
              "and Docker Hub is queried to obtain a list of repositories "
              "under that namespace (e.g., all the repositories of a user). "
              "If not specified, the names are read from stdin."))
    namespace = parser.parse_args(args[1:])

    logging.basicConfig(
        level=logging.DEBUG if namespace.verbose else logging.INFO,
        format="%(message)s")

    return process_files(namespace.files)


if __name__ == "__main__":
    import sys
    failed = main(sys.argv)
    sys.exit(len(failed) > 0)
