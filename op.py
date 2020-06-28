from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, List

from belt import Belt
from pretty import Pretty
from vm import VM


class Instruction(ABC):
    @abstractmethod
    def run(self, vm: VM) -> Optional['Break']:
        pass


class Opcode(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def prefix(self) -> int:
        pass

    @abstractmethod
    def instruction(self, payload) -> Instruction:
        pass


class Break(NamedTuple):
    depth: int
    is_continue: bool


class Block(Pretty):
    def __init__(self, instructions: List[Instruction]) -> None:
        self._instructions = instructions

    def run(self, vm: VM) -> Optional['Break']:
        for ins in self._instructions:
            br = ins.run(vm)
            print(ins, [vm.belt().get_num(i).value.expect_int() for i in range(Belt.SIZE)])
            if br is not None and br.depth > 0:
                return Break(br.depth - 1, is_continue=br.is_continue)
