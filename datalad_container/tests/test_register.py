from datalad.tests.utils_pytest import assert_result_count


def test_register():
    import datalad.api as da
    assert hasattr(da, 'containers_list')
    assert hasattr(da, 'containers_add')
