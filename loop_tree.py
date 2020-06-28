from typing import List, BinaryIO, Optional

import leb128
from adt import adt, Case


@adt
class LoopTree:
    LEAF: Case[int]
    ROLLED_OUT: Case[List[List['LoopTree']]]
    CARTESIAN: Case[int, List['LoopTree']]

    def num_loops(self) -> int:
        return self.match(
            LEAF=lambda n: n,
            ROLLED_OUT=lambda l: len(l),
            CARTESIAN=lambda n, _: n,
        )

    def num_children(self) -> int:
        return self.match(
            LEAF=lambda n: 0,
            ROLLED_OUT=lambda l: len(l[0]) if l else 0,
            CARTESIAN=lambda _, l: len(l),
        )


def parse_loop_trees(reader: BinaryIO) -> List[LoopTree]:
    trees = []
    while True:
        tree = parse_loop_tree(reader)
        if tree is None:
            return trees
        trees.append(tree)


def parse_loop_tree(reader: BinaryIO) -> Optional[LoopTree]:
    kind = reader.read(1)
    if len(kind) == 0:
        return None
    kind = kind[0]
    if kind == 0:
        num_loops, _ = leb128.u.decode_reader(reader)
        return LoopTree.LEAF(num_loops)
    elif kind == 1:
        num_loops, _ = leb128.u.decode_reader(reader)
        num_children, _ = leb128.u.decode_reader(reader)
        matrix = []
        for _ in range(num_loops):
            children = []
            for _ in range(num_children):
                children.append(parse_loop_tree(reader))
            matrix.append(children)
        return LoopTree.ROLLED_OUT(matrix)
    elif kind == 2:
        num_loops, _ = leb128.u.decode_reader(reader)
        num_children, _ = leb128.u.decode_reader(reader)
        children = []
        for _ in range(num_children):
            children.append(parse_loop_tree(reader))
        return LoopTree.CARTESIAN(num_loops, children)
