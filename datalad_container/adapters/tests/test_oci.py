"""Test of oci adapter that do not depend on skopeo or docker being installed.
"""

from datalad_container.adapters import oci
from datalad.tests.utils import (
    assert_raises,
    eq_,
)

# parse_docker_reference


def test_parse_docker_reference():
    eq_(oci.parse_docker_reference("neurodebian").name,
        "neurodebian")


def test_parse_docker_reference_normalize():
    fn = oci.parse_docker_reference
    for name in ["neurodebian",
                 "library/neurodebian",
                 "docker.io/neurodebian"]:
        eq_(fn(name, normalize=True).name,
            "docker.io/library/neurodebian")

    eq_(fn("quay.io/skopeo/stable", normalize=True).name,
        "quay.io/skopeo/stable")


def test_parse_docker_reference_tag():
    fn = oci.parse_docker_reference
    eq_(fn("busybox:1.32"),
        ("busybox", "1.32", None))
    eq_(fn("busybox:1.32", normalize=True),
        ("docker.io/library/busybox", "1.32", None))
    eq_(fn("docker.io/library/busybox:1.32"),
        ("docker.io/library/busybox", "1.32", None))


def test_parse_docker_reference_digest():
    fn = oci.parse_docker_reference
    id_ = "sha256:a9286defaba7b3a519d585ba0e37d0b2cbee74ebfe590960b0b1d6a5e97d1e1d"
    eq_(fn("busybox@{}".format(id_)),
        ("busybox", None, id_))
    eq_(fn("busybox@{}".format(id_), normalize=True),
        ("docker.io/library/busybox", None, id_))
    eq_(fn("docker.io/library/busybox@{}".format(id_)),
        ("docker.io/library/busybox", None, id_))


def test_parse_docker_reference_strip_transport():
    fn = oci.parse_docker_reference
    eq_(fn("docker://neurodebian", strip_transport=True).name,
        "neurodebian")
    eq_(fn("docker-daemon:neurodebian", strip_transport=True).name,
        "neurodebian")


def test_parse_docker_reference_strip_transport_no_transport():
    with assert_raises(ValueError):
        oci.parse_docker_reference("neurodebian", strip_transport=True)
