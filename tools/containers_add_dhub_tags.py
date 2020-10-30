"""Feed tagged Docker Hub images to datalad-containers-add.

This command takes a set of Docker Hub repositories, looks up the
tags, and calls `datalad containers-add ... dhub://REPO:TAG@digest`.  The
output of datalad-container's Docker adapter is dumped to

    images/REPO/TAG/ARCH-DATE-SHORTDIGEST/

where SHORTDIGEST is the first 12 characters of .config.digest key of
the manifest returned by Docker Hub for the image for the arch which was
uploaded on the DATE. In addition, that image record and manifest are
written to a sattelite to that directory .image.json and .manifest.json files.
The step of adding the image is skipped if the path is already present locally.
"""

import fileinput
import json
import logging
from pathlib import Path
from pprint import pprint
import re
import requests

from datalad.api import (
    containers_add,
    save,
)

lgr = logging.getLogger("containers_add_dhub_tags")

REGISTRY_AUTH_URL = ("https://auth.docker.io/token?service=registry.docker.io"
                     "&scope=repository:{repo}:pull")
REGISTRY_ENDPOINT = "https://registry-1.docker.io/v2"
DHUB_ENDPOINT = "https://hub.docker.com/v2"

# TODO: wrap it up with feeding the repositories to consider
# or if we just make it one repository at a time, then could become CLI options
target_architectures = '.*'
target_tags = '.*'

# TEST on busybox on just a few architectures and tags - it is tiny but has too many
#target_architectures = '^(amd64|.*86)$'
#target_tags = '(latest|1.32.0)'

# TODO this could be a CLI option
default_architecture = 'amd64'


def clean_container_name(name):
    """Transform `name` for use in datalad-containers-add.

    Note that, although it probably doesn't matter in practice, this
    transformation is susceptible to conflicts and ambiguity.
    """
    if name.startswith("_/"):
        name = name[2:]
    name = name.replace("_", "-")
    # TODO: research feasibility to create "hierarchical" organization
    # by using . as a separator.  Then we could have a "default"
    # one and then various past instances in  sublevels of
    # .version.architecture.date--shortdigest
    return re.sub(r"[^0-9a-zA-Z-]", "--", name)


def add_container(url, name, target):
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
    return name


def write_json(target, content):
    lgr.info("Writing %s", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(content))
    return target

#
# Registry -- requires authentication to query
#
from contextlib import contextmanager


class RepoRegistry(object):
    def __init__(self, repo):
        resp_auth = requests.get(REGISTRY_AUTH_URL.format(repo=repo))
        resp_auth.raise_for_status()
        self.repo = repo
        self._headers = {
            "Authorization": "Bearer " + resp_auth.json()["token"],
        }

    def get(self, query, headers=None):
        headers = headers or {}
        headers.update(self._headers)
        resp_man = requests.get(f"{REGISTRY_ENDPOINT}/{self.repo}/{query}",
                                headers=headers)
        resp_man.raise_for_status()
        return resp_man.json()

    def get_manifest(self, reference):
        lgr.debug("Getting manifest for %s:%s", self.repo, reference)
        # TODO: Can we check with HEAD first to see if the digest
        # matches what we have locally?
        return self.get(
            f'manifests/{reference}',
            # return the single (first, if multiple e.g. for a reference being a tag)
            # manifest
            headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        )

#
# HUB -- no authentication required
#


def walk_pages(url):
    next_page = url
    while next_page:
        lgr.debug("GET %s", next_page)
        response = requests.get(next_page)
        response.raise_for_status()
        data = response.json()
        next_page = data.get("next")
        yield from data.get("results", [])


def get_repo_tag_images(repo):
    url = f"{DHUB_ENDPOINT}/repositories/{repo}/tags"
    for result in walk_pages(url):
        images = result["images"]
        # there could be records with images not having been uploaded,
        # then it seems digest is not there and 'last_pushed' is None
        for i, image in list(enumerate(images))[::-1]:
            if 'digest' not in image:
                assert not image.get('last_pushed')
                images.pop(i)
        yield result["name"], sorted(images, key=lambda i: i['digest'])


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

        target_architectures_re = re.compile(target_architectures)
        target_tags_re = re.compile(target_tags)
        for repo in repos:
            lgr.info("Working on %s", repo)
            try:
                registry = RepoRegistry(repo)
                #pprint(list(zip(sorted(_all_tags['latest'], key=lambda r: r['digest']), sorted(_all_tags['1.32.0'],
                # key=lambda r: r['digest']))))
                tag_images = dict(get_repo_tag_images(repo))

                # 'latest' tag is special in docker, it is the default one
                # which might typically point to some other release/version.
                # If we find that it is the case, we do not create a dedicated "latest"
                # image/datalad container -- we just add container entry pointing to that
                # one.  If there is no matching one -- we do get "latest"
                latest_matching_tag = None
                if target_tags_re.match('latest'):
                    matching_tags = []
                    for tag, images in tag_images.items():
                        if tag == 'latest' or not target_tags_re.match(tag):
                            lgr.debug("Skipping tag %(tag)s")
                            continue

                        if images == tag_images['latest']:
                            matching_tags.append(tag)
                    if len(matching_tags) >= 1:
                        if len(matching_tags) > 1:
                            lgr.info(
                                "Multiple tags images match latest, taking the first: %s",
                                ', '.join(matching_tags))
                        latest_matching_tag = matching_tags[0]
                        lgr.info("Taking %s as the one for 'latest'", latest_matching_tag)
                else:
                    # TODO: if there is no latest, we should at least establish the
                    # convenient one for each tag
                    pass
                for tag, images in tag_images.items():
                    if tag == 'latest' and latest_matching_tag:
                        continue  # skip since we will handle it
                    if not target_tags_re.match(tag):
                        lgr.debug("Skipping tag %(tag)s")
                        continue
                    for image in images:
                        architecture = image['architecture']
                        if not target_architectures_re.match(architecture):
                            lgr.debug("Skipping architecture %(architecture)s", image)
                            continue
                        manifest = registry.get_manifest(image['digest'])
                        digest = manifest["config"]["digest"]
                        # yoh: if I got it right, it is actual image ID we see in docker images
                        assert digest.startswith("sha256:")
                        digest = digest[7:]
                        digest_short = digest[:12]  # use short version in name
                        last_pushed = image['last_pushed']
                        assert last_pushed.endswith('Z')
                        # take only date
                        last_pushed = last_pushed[:10].replace('-', '')
                        assert len(last_pushed) == 8
                        cleaner_repo = repo
                        # this is how it looks on hub.docker.com URL
                        if repo.startswith('library/'):
                            cleaner_repo = "_/" + cleaner_repo[len('library/'):]
                        # TODO: in case of a single architecture -- do not bother with
                        # {architecture}
                        image_name = (f"{cleaner_repo}/{tag}/{architecture}-{last_pushed}-{digest_short}")
                        dl_container_name = clean_container_name(str(image_name))
                        image_path = Path("images") / image_name
                        url = f"dhub://{repo}:{tag}@{image['digest']}"
                        save_paths = []
                        if image_path.exists():
                            lgr.info("%s already exists, skipping adding", str(image_path))
                        else:
                            save_paths.append(write_json(Path(str(image_path) + '.manifest.json'), manifest))
                            save_paths.append(write_json(Path(str(image_path) + '.image.json'), image))
                            add_container(url, dl_container_name, image_path)
                            # TODO: either fix datalad-container for https://github.com/datalad/datalad-container/issues/98
                            # or here, since we have manifest, we can datalad download-url, and add-archive-content
                            # of the gzipped layers (but without untarring) - that should add datalad-archive
                            # urls to individual layers in the "saved" version
                            # TODO: make it in a single commit with add_container at least,
                            # or one commit for the whole repo sweep
                            save(path=save_paths, message=f"Added manifest and image records for {dl_container_name}")
                        # TODO: ensure .datalad/config to have additional useful fields:
                        #  architecture, os, and manually "updateurl" since not added for
                        #  dhub:// ATM
                        if tag == latest_matching_tag and architecture == default_architecture:
                            # TODO remove section if exists, copy this one
                            lgr.warning("Tracking of 'latest' is not yet implemented")
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
