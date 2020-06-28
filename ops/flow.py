from typing import List, Optional

from op import Instruction, Break, Block
from pretty import Pretty
from vm import VM


class InsNop(Instruction):
    def run(self, vm: VM) -> Optional[Break]:
        pass


class InsUnreachable(Instruction):
    def run(self, vm: VM) -> Optional[Break]:
        raise ValueError('Reached unreachable code')


class InsAlignBlock(Instruction):
    def __init__(self, alignment: int, block: Block) -> None:
        self._alignment = alignment
        self._block = block

    def run(self, vm: VM) -> Optional[Break]:
        previous_alignment = vm.alignment()
        vm.set_alignment(self._alignment)
        br = self._block.run(vm)
        vm.set_alignment(previous_alignment)
        return br


class InsLoopSpecified(Instruction, Pretty):
    def __init__(self, block: Block) -> None:
        self._block = block

    def run(self, vm: VM) -> Optional[Break]:
        vm.loop_stack().start_loop()
        while True:
            if vm.loop_stack().next():
                return None
            br = self._block.run(vm)
            if br is not None:
                if br.depth == 0 and br.is_continue:
                    vm.loop_stack().continue_loop()
                    continue
                vm.loop_stack().break_loop()
                return br


class InsLoopFixed(Instruction, Pretty):
    def __init__(self, num_loops: int, block: Block) -> None:
        self._num_loops = num_loops
        self._block = block

    def run(self, vm: VM) -> Optional[Break]:
        for _ in range(self._num_loops):
            br = self._block.run(vm)
            if br is not None:
                if br.depth == 0 and br.is_continue:
                    vm.loop_stack().continue_loop()
                    continue
                vm.loop_stack().break_loop()
                return br


class InsIfSpecified(Instruction, Pretty):
    def __init__(self, then_block: Block, else_block: Block) -> None:
        self._then_block = then_block
        self._else_block = else_block

    def run(self, vm: VM) -> Optional['Break']:
        raise NotImplemented


class InsIfUnspecified(Instruction, Pretty):
    def __init__(self, condition_idx: int, then_block: Block, else_block: Block) -> None:
        self._condition_idx = condition_idx
        self._then_block = then_block
        self._else_block = else_block

    def run(self, vm: VM) -> Optional['Break']:
        if vm.belt().get_num(self._condition_idx).value.expect_int():
            block = self._then_block
        else:
            block = self._else_block
        br = block.run(vm)
        if br.depth == 0 and br.is_continue:
            raise ValueError('Cannot continue if/else/end block')
        return br


class InsBr(Instruction):
    def __init__(self, br_depth: int):
        self._br_depth = br_depth

    def run(self, vm: VM) -> Optional['Break']:
        return Break(self._br_depth, is_continue=False)


class InsBrIf(Instruction):
    def __init__(self, condition_idx: int, br_depth: int):
        self._condition_idx = condition_idx
        self._br_depth = br_depth

    def run(self, vm: VM) -> Optional['Break']:
        if vm.belt().get_num(self._condition_idx).value.expect_int():
            return Break(self._br_depth, is_continue=False)


class InsBrContinue(Instruction):
    def __init__(self, br_depth: int):
        self._br_depth = br_depth

    def run(self, vm: VM) -> Optional['Break']:
        return Break(self._br_depth, is_continue=True)
