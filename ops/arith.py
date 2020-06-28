import functools
from enum import Enum
from typing import Optional, Callable, List

from belt import BeltNum, Integer, DataType
from op import Break
from op import Instruction
from pretty import Pretty
from vm import VM


class InsRel(Instruction):
    def __init__(self, a_idx: int, b_idx: int, is_signed: bool, op: Callable[[int, int], bool]) -> None:
        self._a_idx = a_idx
        self._b_idx = b_idx
        self._is_signed = is_signed
        self._op = op

    def run(self, vm: VM) -> Optional['Break']:
        a_num = vm.belt().get_num(self._a_idx)
        b_num = vm.belt().get_num(self._b_idx)
        a = a_num.to_signed(self._is_signed).to_int()
        b = b_num.to_signed(self._is_signed).to_int()
        if a is None or b is None:
            vm.belt().push(BeltNum(DataType.I8, Integer(None)))
        else:
            result = self._op(a, b)
            vm.belt().push(BeltNum(DataType.I8, Integer(int(result))))
        return None


class InsRelVerify(Instruction):
    def __init__(self, a_idx: int, b_idx: int, is_signed: bool, op: Callable[[int, int], bool]) -> None:
        self._a_idx = a_idx
        self._b_idx = b_idx
        self._is_signed = is_signed
        self._op = op

    def run(self, vm: VM) -> Optional['Break']:
        a_num = vm.belt().get_num(self._a_idx)
        b_num = vm.belt().get_num(self._b_idx)
        a = a_num.to_signed(self._is_signed).to_int()
        b = b_num.to_signed(self._is_signed).to_int()
        if a is None or b is None or not self._op(a, b):
            raise ValueError('Verify failed')
        return None


class InsNAryOp(Instruction):
    def __init__(self,
                 param_indices: List[int],
                 is_signed: bool,
                 op: Callable[[DataType, int], List[Optional[int]]]
                 ) -> None:
        self._param_indices = param_indices
        self._is_signed = is_signed
        self._op = op

    def run(self, vm: VM) -> Optional['Break']:
        param_nums = [vm.belt().get_num(idx) for idx in self._param_indices]
        params = [num.to_signed(self._is_signed).to_int() for num in param_nums]
        data_type = functools.reduce(DataType.promote, (param.data_type for param in param_nums))
        if any(param is None for param in params):
            vm.belt().push(BeltNum(data_type, Integer(None)))
        else:
            results = self._op(data_type, *params)
            for result in reversed(results):
                vm.belt().push(
                    BeltNum.from_signed(Integer(result), data_type, is_signed=self._is_signed)
                )
        return None


class ArithMode(Enum):
    CHECKED = 0
    WIDENING = 1


class InsArith(InsNAryOp, Pretty):
    def __init__(self,
                 param_indices: List[int],
                 is_signed: bool,
                 arith_mode: ArithMode,
                 arith_op: Callable[[int], int],
                 ) -> None:
        if arith_mode == ArithMode.CHECKED:
            def op(data_type: DataType, *params) -> List[Optional[int]]:
                result = arith_op(*params)
                if result > data_type.max_value(is_signed) or result < data_type.min_value(is_signed):
                    return [None]
                else:
                    return [result]
        elif arith_mode == ArithMode.WIDENING:
            def op(data_type: DataType, *params) -> List[Optional[int]]:
                result = arith_op(*params)
                num_bytes = data_type.num_bytes()
                wide_bytes = result.to_bytes(num_bytes, 'little', signed=is_signed)
                return [
                    int.from_bytes(wide_bytes[num_bytes:], 'little', signed=is_signed),
                    int.from_bytes(wide_bytes[:num_bytes], 'little', signed=is_signed),
                ]
        else:
            raise NotImplemented
        super().__init__(param_indices, is_signed, op)


class InsConvert(Instruction):
    def __init__(self,
                 item_idx: int,
                 data_type: DataType,
                 is_signed: bool,
                 op: Callable[[BeltNum, DataType, bool], BeltNum],
                 ) -> None:
        self._item_idx = item_idx
        self._data_type = data_type
        self._is_signed = is_signed
        self._op = op

    def run(self, vm: VM) -> Optional['Break']:
        item = vm.belt().get_num(self._item_idx)
        vm.belt().push(self._op(item, self._data_type, self._is_signed))
        return None
