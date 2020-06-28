import leb128

from loop_tree import parse_loop_trees, LoopTree
import io


def test_parse_empty():
    assert parse_loop_trees(io.BytesIO(b'')) == []


def test_parse_single_leaf():
    assert parse_loop_trees(io.BytesIO(bytes.fromhex('0003'))) == \
           [LoopTree.LEAF(3)]


def test_parse_multi_leaf():
    assert parse_loop_trees(io.BytesIO(bytes.fromhex('000300ff01007f'))) == \
           [LoopTree.LEAF(3), LoopTree.LEAF(leb128.u.decode(b'\xff\x01')), LoopTree.LEAF(0x7f)]


def test_parse_complex_tree():
    assert parse_loop_trees(
        io.BytesIO(bytes.fromhex(
            '020403' + (
                '0009'
                '010302' + (
                    '0008' '0001'
                    '0000' '0005'
                    '0007' '0002'
                ) +
                '020601' '0003'
            ) +
            '010201' + (
                '000a'
                '0002'
            )
        ))
    ) == [
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
            [LoopTree.LEAF(0xa)],
            [LoopTree.LEAF(2)],
        ]),
    ]
