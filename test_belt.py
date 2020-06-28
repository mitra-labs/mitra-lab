import pytest

from belt import DataType


@pytest.mark.parametrize(
    "data_type,is_signed,expected",
    [
        (DataType.I8, False, 0xff),
        (DataType.I8, True, 0x7f),
        (DataType.I16, False, 0xffff),
        (DataType.I16, True, 0x7fff),
        (DataType.I32, False, 0xffff_ffff),
        (DataType.I32, True, 0x7fff_ffff),
        (DataType.I64, False, 0xffff_ffff_ffff_ffff),
        (DataType.I64, True, 0x7fff_ffff_ffff_ffff),
    ]
)
def test_data_type_max(data_type: DataType, is_signed: bool, expected: int):
    assert data_type.max_value(is_signed) == expected


@pytest.mark.parametrize(
    "data_type,is_signed,expected",
    [
        (DataType.I8, False, 0),
        (DataType.I8, True, -0x80),
        (DataType.I16, False, 0),
        (DataType.I16, True, -0x8000),
        (DataType.I32, False, 0),
        (DataType.I32, True, -0x8000_0000),
        (DataType.I64, False, 0),
        (DataType.I64, True, -0x8000_0000_0000_0000),
    ]
)
def test_data_type_min(data_type: DataType, is_signed: bool, expected: int):
    assert data_type.min_value(is_signed) == expected
