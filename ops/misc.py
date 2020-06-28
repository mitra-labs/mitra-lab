from typing import Optional

from belt import BeltNum, DataType, Integer
from op import Break
from op import Instruction
from pretty import Pretty
from vm import VM


class InsConst(Instruction, Pretty):
    def __init__(self, belt_num: BeltNum) -> None:
        self._belt_num = belt_num

    def run(self, vm: VM) -> Optional['Break']:
        vm.belt().push(self._belt_num)
        return None


class InsLocalGet(Instruction, Pretty):
    def __init__(self, local_idx: int) -> None:
        self._local_idx = local_idx

    def run(self, vm: VM) -> Optional['Break']:
        vm.belt().push(vm.local(self._local_idx))
        return None


class InsLocalSet(Instruction, Pretty):
    def __init__(self, local_idx: int) -> None:
        self._local_idx = local_idx

    def run(self, vm: VM) -> Optional['Break']:
        vm.set_local(self._local_idx, vm.belt()[0])
        return None


class InsIsErr(Instruction, Pretty):
    def __init__(self, item_idx: int) -> None:
        self._item_idx = item_idx

    def run(self, vm: VM) -> Optional['Break']:
        num = vm.belt().get_num(self._item_idx)
        vm.belt().push(BeltNum(DataType.I8, Integer(
            1 if num.value.to_int() is None else 0
        )))
        return None


class InsVerify(Instruction, Pretty):
    def __init__(self, item_idx: int) -> None:
        self._item_idx = item_idx

    def run(self, vm: VM) -> Optional['Break']:
        num = vm.belt().get_num(self._item_idx)
        if num.value.to_int() is None or num.value.to_int() == 0:
            raise ValueError('Verify failed')
        return None


class InsVerifyOk(Instruction, Pretty):
    def __init__(self, item_idx: int) -> None:
        self._item_idx = item_idx

    def run(self, vm: VM) -> Optional['Break']:
        num = vm.belt().get_num(self._item_idx)
        if num.value.to_int() is None:
            raise ValueError('Verify failed')
        return None


class InsSliceLen(Instruction, Pretty):
    def __init__(self, slice_idx: int) -> None:
        self._slice_idx = slice_idx

    def run(self, vm: VM) -> Optional['Break']:
        slc = vm.belt().get_slice(self._slice_idx)
        vm.belt().push(BeltNum(DataType.I32, Integer(slc.length)))
        return None


class InsSliceOp(Instruction, Pretty):
    def __init__(self, slice_idx: int, num_bytes_idx: int, op) -> None:
        self._slice_idx = slice_idx
        self._num_bytes_idx = num_bytes_idx
        self._op = op

    def run(self, vm: VM) -> Optional['Break']:
        slc = vm.belt().get_slice(self._slice_idx)
        num_bytes = vm.belt().get_num(self._num_bytes_idx).value.expect_int()
        vm.belt().push(self._op(slc, num_bytes))
        return None


class InsSubSlice(Instruction, Pretty):
    def __init__(self, slice_idx: int, start_idx: int, length_idx: int) -> None:
        self._slice_idx = slice_idx
        self._start_idx = start_idx
        self._length_idx = length_idx

    def run(self, vm: VM) -> Optional['Break']:
        slc = vm.belt().get_slice(self._slice_idx)
        start = vm.belt().get_num(self._start_idx).value.expect_int()
        length = vm.belt().get_num(self._length_idx).value.expect_int()
        vm.belt().push(slc.subslice(start, length))
        return None


class InsLoad(Instruction, Pretty):
    def __init__(self, data_type: DataType, slice_idx: int, offset: int) -> None:
        self._data_type = data_type
        self._slice_idx = slice_idx
        self._offset = offset

    def run(self, vm: VM) -> Optional['Break']:
        slc = vm.belt().get_slice(self._slice_idx)
        vm.belt().push(slc.load(self._data_type, self._offset))
        return None


class InsStore(Instruction, Pretty):
    def __init__(self, item_idx: int, slice_idx: int, offset: int) -> None:
        self._item_idx = item_idx
        self._slice_idx = slice_idx
        self._offset = offset

    def run(self, vm: VM) -> Optional['Break']:
        slc = vm.belt().get_slice(self._slice_idx)
        num = vm.belt().get_num(self._item_idx)
        slc.store(self._offset, num)
        return None
