import pytest

from loop_stack import LoopStack
from loop_tree import LoopTree


def test_loop_stack_leaf():
    stack = LoopStack([
        LoopTree.LEAF(9),
    ])
    stack.start_loop()
    for _ in range(9):
        assert not stack.next()
    assert stack.next()
    with pytest.raises(ValueError) as ex:
        stack.next()
    assert 'No current loop' == str(ex.value)


def test_loop_stack_nested():
    stack = LoopStack([
        LoopTree.CARTESIAN(3, [
            LoopTree.LEAF(2),
            LoopTree.LEAF(4),
        ]),
    ])
    stack.start_loop()
    for j in range(3):
        assert not stack.next()

        stack.start_loop()
        for i in range(2):
            assert not stack.next()
        assert stack.next()

        stack.start_loop()
        for i in range(4):
            assert not stack.next()
        assert stack.next()

    assert stack.next()

    with pytest.raises(ValueError) as ex:
        stack.next()
    assert 'No current loop' == str(ex.value)


def test_loop_stack_nested2():
    stack = LoopStack([
        LoopTree.CARTESIAN(2, [
            LoopTree.ROLLED_OUT([
                [LoopTree.LEAF(3), LoopTree.LEAF(1)],
                [LoopTree.LEAF(4), LoopTree.LEAF(2)],
            ]),
        ]),
    ])
    stack.start_loop()
    for _ in range(2):
        assert not stack.next()

        stack.start_loop()
        for loop1, loop2 in [(3, 1), (4, 2)]:
            assert not stack.next()

            stack.start_loop()
            for _ in range(loop1):
                assert not stack.next()
            assert stack.next()

            stack.start_loop()
            for _ in range(loop2):
                assert not stack.next()
            assert stack.next()
        assert stack.next()
    assert stack.next()

    with pytest.raises(ValueError) as ex:
        stack.next()
    assert 'No current loop' == str(ex.value)


def test_loop_stack_complex_no_break():
    stack = LoopStack([
        LoopTree.CARTESIAN(4, [
            LoopTree.LEAF(9),
            LoopTree.ROLLED_OUT([
                [LoopTree.LEAF(8), LoopTree.LEAF(1)],
                [LoopTree.LEAF(0), LoopTree.LEAF(5)],
                [LoopTree.LEAF(7), LoopTree.LEAF(2)],
            ]),
            LoopTree.CARTESIAN(6, [
                LoopTree.LEAF(3),
            ]),
        ]),
        LoopTree.ROLLED_OUT([
            [LoopTree.LEAF(10)],
            [LoopTree.LEAF(2)],
        ]),
    ])
    stack.start_loop()
    for _ in range(4):
        assert not stack.next()

        stack.start_loop()
        for _ in range(9):
            assert not stack.next()
        assert stack.next()

        stack.start_loop()
        for loop1, loop2 in [(8, 1), (0, 5), (7, 2)]:
            assert not stack.next()

            stack.start_loop()
            for _ in range(loop1):
                assert not stack.next()
            assert stack.next()

            stack.start_loop()
            for _ in range(loop2):
                assert not stack.next()
            assert stack.next()
        assert stack.next()

        stack.start_loop()
        for _ in range(6):
            assert not stack.next()

            stack.start_loop()
            for _ in range(3):
                assert not stack.next()
            assert stack.next()
        assert stack.next()
    assert stack.next()

    stack.start_loop()
    for loop in [10, 2]:
        assert not stack.next()

        stack.start_loop()
        for _ in range(loop):
            assert not stack.next()
        assert stack.next()
    assert stack.next()

    with pytest.raises(ValueError) as ex:
        stack.next()
    assert 'No current loop' == str(ex.value)
