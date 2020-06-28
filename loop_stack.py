from dataclasses import dataclass
from typing import List

from loop_tree import LoopTree


@dataclass
class LoopStackItem:
    tree: LoopTree
    position: int
    inner_position: int


class LoopStack:
    def __init__(self, loop_trees: List[LoopTree]):
        self._loop_trees = loop_trees
        self._loop_index = 0
        self._stack: List[LoopStackItem] = []

    def start_loop(self):
        if not self._stack:
            tree = self._loop_trees[self._loop_index]
            self._stack.append(LoopStackItem(
                tree=tree,
                position=0,
                inner_position=0,
            ))
            self._loop_index += 1
        else:
            top = self._stack[-1]

            def leaf(_):
                raise ValueError('Cannot start loop in leaf')

            def nested_loop(t: LoopTree):
                self._stack.append(LoopStackItem(
                    tree=t,
                    position=0,
                    inner_position=0,
                ))
                top.inner_position += 1

            def rolled_out(matrix):
                if top.position == 0:
                    raise ValueError('Tried starting loop within loop before any iteration')
                if top.position > len(matrix):
                    raise ValueError('Iterated rolled out loop too far')
                if top.inner_position >= len(matrix[top.position - 1]):
                    raise ValueError('Tried starting a non-existing loop in a rolled out loop')
                nested_loop(matrix[top.position - 1][top.inner_position])

            def cartesian(n, children):
                if top.position == 0:
                    raise ValueError('Tried starting loop within loop before any iteration')
                if top.position > n:
                    raise ValueError('Iterated cartesian loop too far')
                if top.inner_position >= len(children):
                    raise ValueError('Tried starting a non-existing loop in a rolled out loop')
                nested_loop(children[top.inner_position])

            top.tree.match(
                LEAF=leaf,
                ROLLED_OUT=rolled_out,
                CARTESIAN=cartesian,
            )

    def next(self) -> bool:
        if not self._stack:
            raise ValueError('No current loop')
        top = self._stack[-1]

        if top.position == top.tree.num_loops():
            self._stack.pop()
            if self._stack:
                top = self._stack[-1]
                if top.inner_position == top.tree.num_children():
                    top.inner_position = 0
            return True
        top.position += 1

        return False

    def break_loop(self):
        if not self._stack:
            raise ValueError('No current loop')
        self._stack.pop()
        if self._stack:
            top = self._stack[-1]
            top.inner_position += 1
            if top.inner_position == top.tree.num_children():
                top.inner_position = 0

    def continue_loop(self):
        if not self._stack:
            raise ValueError('No current loop')
        top = self._stack[-1]
        top.inner_position = 0

    def __str__(self):
        return f'LoopStack<{self._stack}>'
