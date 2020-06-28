import pytest

from belt import BeltNum, DataType, Integer, Belt
from loop_stack import LoopStack
from loop_tree import LoopTree
from op import Block
from ops.arith import InsArith, ArithMode, InsRel
from ops.flow import InsLoopSpecified, InsBrIf
from ops.misc import InsConst, InsLocalSet, InsLocalGet
from vm import VM


def test_simple_loop():
    vm = VM(
        LoopStack([
            LoopTree.LEAF(8),
        ]),
        num_locals=0,
        ram_size=0,
    )
    ins = InsLoopSpecified(Block([
        InsArith([0], False, ArithMode.CHECKED, lambda n: n + 1),
    ]))
    ins.run(vm)
    result = vm.belt().get_num(0).value.expect_int()
    assert result == 8


def test_fib_loop():
    vm = VM(
        LoopStack([
            LoopTree.LEAF(16),
        ]),
        num_locals=0,
        ram_size=0,
    )
    ins = Block([
        InsConst(BeltNum(DataType.I64, Integer(1))),
        InsLoopSpecified(Block([
            InsArith([0, 1], False, ArithMode.CHECKED, int.__add__),
        ])),
    ])
    ins.run(vm)
    belt = [vm.belt().get_num(i).value.expect_int() for i in range(Belt.SIZE)]
    assert belt == [1597, 987, 610, 377, 233, 144, 89, 55, 34, 21, 13, 8, 5, 3, 2, 1]


def test_nested_loop():
    vm = VM(
        LoopStack([
            LoopTree.CARTESIAN(3, [
                LoopTree.LEAF(3),
                LoopTree.LEAF(5),
            ]),
        ]),
        num_locals=0,
        ram_size=0,
    )
    ins = InsLoopSpecified(Block([
        InsLoopSpecified(Block([
            InsArith([0], True, ArithMode.CHECKED, lambda n: n - 1),
        ])),
        InsLoopSpecified(Block([
            InsArith([0], True, ArithMode.CHECKED, lambda n: n + 1),
        ])),
        InsArith([0], True, ArithMode.CHECKED, lambda n: n * 2),
    ]))
    ins.run(vm)
    result = vm.belt().get_num(0).value.expect_int()
    assert result == 28


def test_simple_loop_break():
    vm = VM(
        LoopStack([
            LoopTree.LEAF(8),
        ]),
        num_locals=0,
        ram_size=0,
    )
    ins = InsLoopSpecified(Block([
        InsBrIf(condition_idx=0, br_depth=1),
        InsArith([2], False, ArithMode.CHECKED, lambda n: n + 1),
        InsConst(BeltNum(DataType.I8, Integer(3))),
        InsRel(a_idx=0, b_idx=1, is_signed=False, op=lambda a, b: a < b),
    ]))
    ins.run(vm)
    belt = [vm.belt().get_num(i).value.expect_int() for i in range(Belt.SIZE)]
    assert belt == [1, 3, 4,
                    0, 3, 3,
                    0, 3, 2,
                    0, 3, 1,
                    0, 0, 0, 0]


def test_two_simple_loops_break():
    vm = VM(
        LoopStack([
            LoopTree.LEAF(16),
            LoopTree.LEAF(16),
        ]),
        num_locals=1,
        ram_size=0,
    )
    ins = Block([
        InsLoopSpecified(Block([
            InsArith([0], False, ArithMode.CHECKED, lambda n: n + 1),
            InsLocalSet(0),
            InsConst(BeltNum(DataType.I8, Integer(3))),
            InsRel(a_idx=0, b_idx=1, is_signed=False, op=lambda a, b: a < b),
            InsBrIf(condition_idx=0, br_depth=1),
            InsLocalGet(0),
        ])),
        InsLoopSpecified(Block([
            InsArith([0], False, ArithMode.CHECKED, lambda n: n + 1),
            InsLocalSet(0),
            InsConst(BeltNum(DataType.I8, Integer(7))),
            InsRel(a_idx=0, b_idx=1, is_signed=False, op=lambda a, b: a < b),
            InsBrIf(condition_idx=0, br_depth=1),
            InsLocalGet(0),
        ])),
    ])
    ins.run(vm)
    belt = [vm.belt().get_num(i).value.expect_int() for i in range(Belt.SIZE)]
    assert belt == [1, 7, 8, 7,
                    0, 7, 7, 6,
                    0, 7, 6, 5,
                    0, 7, 5, 4]
    assert vm.local(0).value.expect_int() == 8


def test_nested_loop_break():
    vm = VM(
        LoopStack([
            LoopTree.CARTESIAN(3, [
                LoopTree.LEAF(3),
                LoopTree.LEAF(5),
            ]),
            LoopTree.LEAF(2),
        ]),
        num_locals=1,
        ram_size=0,
    )
    ins = Block([
        InsLoopSpecified(Block([
            # decrement 3 times
            InsLoopSpecified(Block([
                InsArith([0], True, ArithMode.CHECKED, lambda n: n - 1),
            ])),
            # increment 5 times; if number reaches 10, terminate outer loop
            InsLoopSpecified(Block([
                InsArith([0], True, ArithMode.CHECKED, lambda n: n + 1),
                InsLocalSet(0),
                InsConst(BeltNum(DataType.I8, Integer(10))),
                InsRel(0, 1, True, lambda a, b: a < b),
                InsBrIf(0, 2),
                InsLocalGet(0),
            ])),
            # double
            InsArith([0], True, ArithMode.CHECKED, lambda n: n * 2),
        ])),
        InsLocalGet(0),
        InsLoopSpecified(Block([
            InsArith([0], True, ArithMode.CHECKED, lambda n: n + 2),
        ])),
    ])
    ins.run(vm)
    belt = [vm.belt().get_num(i).value.expect_int() for i in range(Belt.SIZE)]
    assert belt == [15, 13,  # 2 times  +2
                    11,  # local get
                    1, 10, 11,  # final loop iteration
                    10, 0, 10, 10,  # second to last loop iteration
                    9, 10, 11,  # decrementing loop
                    12,  # *2
                    6, 0]  # local get, rel
