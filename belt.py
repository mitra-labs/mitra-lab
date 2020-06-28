import functools
from enum import Enum
from typing import Optional, Union, NamedTuple, List

BeltItem = Union['BeltSlice', 'BeltNum']


class Belt:
    SIZE = 16

    def __init__(self):
        self._items: List[BeltItem] = [BeltNum(data_type=DataType.I8, value=Integer(0))] * Belt.SIZE

    def __getitem__(self, item: int) -> BeltItem:
        return self._items[item]

    def get_num(self, item: int) -> 'BeltNum':
        item = self._items[item]
        if isinstance(item, BeltSlice):
            raise ValueError('Expected num, got slice')
        return item

    def get_slice(self, item: int) -> 'BeltSlice':
        item = self._items[item]
        if isinstance(item, BeltNum):
            raise ValueError('Expected slice, got num')
        return item

    def push(self, value: BeltItem):
        self._items.pop(-1)
        self._items.insert(0, value)


class DataType(Enum):
    I8 = 8
    I16 = 16
    I32 = 32
    I64 = 64

    def mod_value(self, is_signed: bool) -> int:
        bits = self.value
        val = 1 << (bits - is_signed)
        return val

    def max_value(self, is_signed: bool) -> int:
        bits = self.value
        val = 1 << (bits - is_signed)
        return val - 1

    def min_value(self, is_signed: bool) -> int:
        if is_signed:
            bits = self.value
            return -(1 << (bits - 1))
        return 0

    def promote(self, other: 'DataType') -> 'DataType':
        return DataType(max(self.value, other.value))

    def num_bytes(self) -> int:
        return self.value // 8


class Integer:
    def __init__(self, value: Optional[int]):
        self._value = value

    @staticmethod
    def _binary_func(f):
        @functools.wraps(f)
        def wrapped(self: 'Integer', other) -> 'Integer':
            if isinstance(other, Integer):
                if other._value is None:
                    return Integer(None)
                other = other._value
            if self._value is None:
                return Integer(None)
            return Integer(f(self._value, other))
        return wrapped

    __add__ = _binary_func.__func__(int.__add__)
    __sub__ = _binary_func.__func__(int.__sub__)
    __mul__ = _binary_func.__func__(int.__mul__)
    __floordiv__ = _binary_func.__func__(int.__floordiv__)
    __mod__ = _binary_func.__func__(int.__mod__)
    __divmod__ = _binary_func.__func__(int.__divmod__)
    __lshift__ = _binary_func.__func__(int.__lshift__)
    __rshift__ = _binary_func.__func__(int.__rshift__)
    __and__ = _binary_func.__func__(int.__and__)
    __or__ = _binary_func.__func__(int.__or__)
    __xor__ = _binary_func.__func__(int.__xor__)

    __radd__ = _binary_func.__func__(int.__radd__)
    __rsub__ = _binary_func.__func__(int.__rsub__)
    __rmul__ = _binary_func.__func__(int.__rmul__)
    __rfloordiv__ = _binary_func.__func__(int.__rfloordiv__)
    __rmod__ = _binary_func.__func__(int.__rmod__)
    __rdivmod__ = _binary_func.__func__(int.__rdivmod__)
    __rlshift__ = _binary_func.__func__(int.__rlshift__)
    __rrshift__ = _binary_func.__func__(int.__rrshift__)
    __rand__ = _binary_func.__func__(int.__rand__)
    __ror__ = _binary_func.__func__(int.__ror__)
    __rxor__ = _binary_func.__func__(int.__rxor__)

    def to_int(self) -> Optional[int]:
        return self._value

    def expect_int(self) -> int:
        if self._value is None:
            raise ValueError('Expected int, got Err')
        return self._value

    def __repr__(self):
        return f'Integer({self._value})'


class BeltNum(NamedTuple):
    data_type: DataType
    value: Integer

    def to_signed(self, is_signed: bool) -> 'Integer':
        if is_signed:
            val = self.value.to_int()
            if val is None:
                return Integer(None)
            int_bytes = val.to_bytes(self.data_type.num_bytes(), 'little', signed=False)
            return Integer(int.from_bytes(int_bytes, 'little', signed=True))
        return self.value

    @staticmethod
    def from_signed(val: Integer, data_type: DataType, is_signed: bool) -> 'BeltNum':
        val = val.to_int()
        if val is None:
            return BeltNum(data_type=data_type, value=Integer(None))
        int_bytes = val.to_bytes(data_type.num_bytes(), 'little', signed=is_signed)
        return BeltNum(
            data_type=data_type,
            value=Integer(int.from_bytes(int_bytes, 'little', signed=False))
        )

    def wrap(self, data_type: DataType) -> 'BeltNum':
        if self.data_type.value < data_type.value:
            raise ValueError(f'Cannot use wrap to up-cast value from'
                             f'{self.data_type} to {data_type}')
        if self.data_type == data_type:
            return self
        return BeltNum(
            data_type=data_type,
            value=self.value % data_type.mod_value(False)
        )

    def cast_sat(self, data_type: DataType, is_signed: bool) -> 'BeltNum':
        if self.data_type.value < data_type.value:
            raise ValueError(f'Cannot use cast_sat to up-cast value from'
                             f'{self.data_type} to {data_type}')
        if self.data_type == data_type:
            return self
        val = self.to_signed(is_signed).to_int()
        if val is None:
            return BeltNum(data_type, Integer(None))
        val = max(val, data_type.min_value(is_signed))
        val = min(val, data_type.max_value(is_signed))
        return BeltNum.from_signed(Integer(val), data_type=data_type, is_signed=is_signed)

    def cast_checked(self, data_type: DataType, is_signed: bool) -> 'BeltNum':
        if self.data_type.value < data_type.value:
            raise ValueError(f'Cannot use cast_checked to up-cast value from'
                             f'{self.data_type} to {data_type}')
        if self.data_type == data_type:
            return self
        val = self.to_signed(is_signed).to_int()
        if val is None or \
                val < data_type.min_value(is_signed) or \
                val > data_type.max_value(is_signed):
            return BeltNum(data_type, Integer(None))
        return BeltNum.from_signed(Integer(val), data_type=data_type, is_signed=is_signed)

    def extend(self, data_type: DataType, is_signed: bool) -> 'BeltNum':
        if self.data_type.value > data_type.value:
            raise ValueError(f'Cannot use extend to down-cast value from'
                             f'{self.data_type} to {data_type}')
        if self.data_type == data_type:
            return self
        val = self.to_signed(is_signed).to_int()
        return BeltNum.from_signed(Integer(val), data_type=data_type, is_signed=is_signed)

    def binary_op(self, other: 'BeltNum', is_signed: bool, f) -> 'BeltNum':
        data_type = self.data_type.promote(other.data_type)
        a = self.extend(data_type, is_signed)
        b = other.extend(data_type, is_signed)
        return BeltNum.from_signed(f(a, b), data_type, is_signed=is_signed)


class BeltSlice(NamedTuple):
    data: Union[bytes, bytearray]
    start: int
    length: int

    def trim_l(self, num_bytes: int) -> 'BeltSlice':
        if num_bytes < 0 or num_bytes > self.length:
            raise ValueError('Tried trimming beyond slice boundaries')
        return BeltSlice(self.data, start=self.start + num_bytes, length=self.length - num_bytes)

    def trim_r(self, num_bytes: int) -> 'BeltSlice':
        if num_bytes < 0 or num_bytes > self.length:
            raise ValueError('Tried trimming beyond slice boundaries')
        return BeltSlice(self.data, start=self.start, length=self.length - num_bytes)

    def shrink(self, num_bytes: int) -> 'BeltSlice':
        if num_bytes < 0 or num_bytes > self.length:
            raise ValueError('Tried shrinking beyond slice boundaries')
        return BeltSlice(self.data, start=self.start, length=self.length - num_bytes)

    def subslice(self, start: int, length: int) -> 'BeltSlice':
        if start < 0 or length < 0 or start + length > self.length:
            raise ValueError('Tried shrinking beyond slice boundaries')
        return BeltSlice(self.data, start=self.start + start, length=length)

    def load(self, data_type: DataType, offset: int) -> BeltNum:
        if offset < 0:
            raise ValueError('Offset is negative')
        num_bytes = data_type.num_bytes()
        if offset + num_bytes > self.length:
            return BeltNum(data_type, Integer(None))
        i = self.start + offset
        int_bytes = self.data[i:i + num_bytes]
        return BeltNum(data_type, Integer(int.from_bytes(int_bytes, 'little', signed=False)))

    def store(self, offset: int, num: BeltNum) -> None:
        if offset < 0:
            raise ValueError('Offset is negative')
        num_bytes = num.data_type.num_bytes()
        val = num.value.to_int()
        if val is None:
            return
        if isinstance(self.data, bytes):
            raise ValueError('Cannot store in write-only slice')
        if offset + num_bytes > self.length:
            raise ValueError('Tried writing value out of bounds')
        int_bytes = val.to_bytes(num_bytes, 'little', signed=False)
        i = self.start + offset
        self.data[i:i + num_bytes] = int_bytes
