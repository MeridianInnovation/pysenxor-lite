import numpy as np
import pytest

from senxor.proc import colormaps


class TestLazyLutDictInterface:
    def test_len(self):
        assert len(colormaps) > 0

    def test_contains(self):
        keys = list(colormaps.keys())
        assert len(keys) > 0
        assert keys[0] in colormaps
        assert "nonexistent" not in colormaps

    def test_iter(self):
        keys_from_iter = list(colormaps)
        keys_from_keys = list(colormaps.keys())
        assert keys_from_iter == keys_from_keys

    def test_getitem_valid(self):
        keys = list(colormaps.keys())
        for key in keys:
            lut = colormaps[key]
            assert isinstance(lut, np.ndarray)
            assert lut.dtype == np.uint8
            assert lut.ndim == 2
            assert lut.shape[1] == 3

    def test_getitem_invalid(self):
        with pytest.raises(KeyError):
            _ = colormaps["nonexistent"]  # type: ignore[reportArgumentType]


class TestLazyLoading:
    def test_lazy_loading(self):
        fresh_dict = type(colormaps)()
        key = next(iter(fresh_dict.keys()))
        assert key not in fresh_dict.data  # type: ignore[reportAttributeIssue]
        _ = fresh_dict[key]
        assert key in fresh_dict.data  # type: ignore[reportAttributeIssue]

    def test_cache_reuse(self):
        fresh_dict = type(colormaps)()
        key = next(iter(fresh_dict.keys()))
        lut1 = fresh_dict[key]
        lut2 = fresh_dict[key]
        assert lut1 is lut2


class TestMappingContract:
    def test_items(self):
        items_count = 0
        for key, lut in colormaps.items():
            assert key in colormaps
            assert isinstance(lut, np.ndarray)
            assert lut.shape[1] == 3
            items_count += 1
        assert items_count == len(colormaps)

    def test_values(self):
        values_count = 0
        for lut in colormaps.values():
            assert isinstance(lut, np.ndarray)
            assert lut.shape[1] == 3
            values_count += 1
        assert values_count == len(colormaps)
