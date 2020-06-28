from belt import Belt, BeltNum, DataType, Integer, BeltSlice, BeltItem
from loop_stack import LoopStack


class VM:
    def __init__(self, loop_stack: LoopStack, num_locals: int, ram_size: int):
        self._belt = Belt()
        self._loop_stack = loop_stack
        self._locals = [BeltNum(data_type=DataType.I8, value=Integer(0))] * num_locals
        self._ram = BeltSlice(bytearray(ram_size), 0, ram_size)
        self._alignment = 0

    def belt(self) -> Belt:
        return self._belt

    def loop_stack(self) -> LoopStack:
        return self._loop_stack

    def local(self, local_idx: int) -> BeltItem:
        return self._locals[local_idx]

    def set_local(self, local_idx: int, item: BeltItem) -> None:
        self._locals[local_idx] = item

    def ram(self) -> BeltSlice:
        return self._ram

    def alignment(self) -> int:
        return self._alignment

    def set_alignment(self, alignment: int) -> None:
        self._alignment = alignment
