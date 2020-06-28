from dataclasses import dataclass
from itertools import zip_longest
from typing import List, Dict, Tuple, NamedTuple, Set, Optional

from lark import Lark, Tree

from belt import BeltNum, DataType, Integer, Belt, BeltSlice
from op import Instruction, Block
from ops.arith import InsArith, ArithMode, InsRel, InsRelVerify, InsNAryOp, InsConvert
from ops.flow import InsLoopSpecified, InsIfUnspecified, InsUnreachable, InsNop, InsBr, InsBrIf, InsBrContinue
from ops.misc import InsConst, InsLocalSet, InsLocalGet, InsVerify, InsVerifyOk, InsIsErr, InsSliceLen, InsSliceOp, \
    InsSubSlice, InsLoad, InsStore

import re

grammar = r"""
start: version statement*
version: "version" VERSION ";"
statement: loop | if | assign | call_stmt | store | load
loop: "loop" NAME "{" statement* "}"
assign: assign_target "=" expr ";"
call_stmt: call ";"
store: NAME "[" OFFSET "]" "=" NAME ";"
load: NAME "=" NAME "[" OFFSET "]" "as" TYPE ";"
if: "if" NAME then else?
then: "{" statement* "}"
else: "else" "{" statement* "}"
expr: lit | name | call | operation | slicing
call: NAME "(" params ")"
params: (NAME ",")* (NAME ","?)?
assign_target: local_name | assign_target_names
assign_target_names: (NAME ",")* NAME ","?
name: NAME | LOCAL_NAME
local_name: LOCAL_NAME
operation: NAME OPERATOR NAME
slicing: NAME "[" NAME? SLICE_SEP NAME? "]"
lit: NUM
VERSION: /\d+\.\d+\.\d+/
NAME: /[a-zA-Z0-9_]+/
LOCAL_NAME: /\$[a-zA-Z0-9_]+/
NUM: /(-?\d[\d_]*)(i|u)(8|16|32|64)/
TYPE: /(i|u)(8|16|32|64)/
OFFSET: /\d+/
OPERATOR: "_+_" | "_-_" | "_*_" | "+" | "-" | "*" | "/" | "%" | "<<" | ">>" | "&" | "|" | "^" | "==" | "!=" | "<" | "<=" | ">" | ">="
SLICE_SEP: ".."
COMMENT: /#.*/
%ignore COMMENT
%ignore " "
%ignore "\t"
%ignore "\n"
"""


class CompilerBeltItem(NamedTuple):
    name: str
    is_signed: Optional[bool]
    is_slice: bool
    is_consistent: bool = True
    other_item: Optional['CompilerBeltItem'] = None


class CompilerLocal(NamedTuple):
    is_signed: Optional[bool]
    is_slice: bool
    local_idx: int


@dataclass
class Scope:
    scope_name: Optional[str]
    belt_items: Set[str]
    out_of_scope_access: List[str]


class CompileResult(NamedTuple):
    instructions: List[Instruction]
    num_locals: int


class Compiler:
    VERSION = '0.0.1'
    REG_LIT = re.compile(r'^(-?\d+)([iu])(8|16|32|64)$')
    REG_TYPE = re.compile(r'^([iu])(8|16|32|64)$')
    REG_CAST = re.compile(r'(cast_extend|cast_warp|cast_sat|cast_checked)(8|16|32|64)')

    def __init__(self) -> None:
        self._grammar = Lark(grammar)
        self._belt: List[CompilerBeltItem] = []
        self._locals: Dict[str, CompilerLocal] = {}
        self._scopes: List[Scope] = []

    def compile(self, src: str) -> CompileResult:
        tree = self._grammar.parse(src)
        instructions = self._handle_program(tree)
        return CompileResult(instructions, len(self._locals))

    def _push(self, item: CompilerBeltItem):
        del self._belt[Belt.SIZE:]
        self._belt.insert(0, item)
        if self._scopes:
            self._scopes[-1].belt_items.add(item.name)

    def _begin_scope(self, name: Optional[str]):
        self._scopes.append(Scope(name, set(), []))

    def _end_scope(self):
        self._scopes.pop()

    def _get_item(self, name: str, assert_is_slice: Optional[bool] = None) -> Tuple[int, CompilerBeltItem]:
        for idx, item in enumerate(self._belt):
            if item.name == name:
                if not item.is_consistent:
                    raise ValueError(f"Inconsistent belt item (due to branch), got {item}")
                if assert_is_slice is not None and item.is_slice != assert_is_slice:
                    raise ValueError(f"Invalid type: {name} is a {'number' if assert_is_slice else 'slice'}")
                if self._scopes:
                    if item.name not in self._scopes[-1].belt_items:
                        self._scopes[-1].out_of_scope_access.append(item.name)
                return idx, item
        raise ValueError(f"Belt item with the name `{name}` not found, maybe it's pushed of the belt? "
                         f"Consider using locals in this case.")

    def _handle_program(self, tree: Tree) -> List[Instruction]:
        version, *statements = tree.children
        self._handle_version(version)
        return self._handle_statements(statements)

    def _handle_version(self, tree: Tree):
        version_token, = tree.children
        if version_token != self.VERSION:
            raise ValueError(f"Unsupported version (possible versions: {self.VERSION})")

    def _handle_statements(self, stmts: List[Tree]) -> List[Instruction]:
        code = []
        for stmt in stmts:
            stmt, = stmt.children
            code.extend(self._handle_statement(stmt))
        return code

    def _handle_statement(self, stmt: Tree) -> List[Instruction]:
        if stmt.data == 'loop':
            return self._handle_loop(stmt)
        elif stmt.data == 'if':
            return self._handle_if(stmt)
        elif stmt.data == 'assign':
            return self._handle_assign(stmt)
        elif stmt.data == 'call_stmt':
            return self._handle_call_stmt(stmt)
        elif stmt.data == 'store':
            return self._handle_store(stmt)
        elif stmt.data == 'load':
            return self._handle_load(stmt)
        else:
            raise ValueError(f"Unexpected statement {stmt}")

    def _handle_loop(self, loop: Tree) -> List[Instruction]:
        name, *statements = loop.children
        belt_before_loop = self._belt.copy()
        self._begin_scope(name)
        code = self._handle_statements(statements)
        scope = self._scopes[-1]
        for name in scope.out_of_scope_access:
            for new_idx, new_item in enumerate(self._belt):
                if new_item.name == name:
                    break
            else:
                raise ValueError(f'Invalid loop: loop variable {name} not on belt')
            for old_idx, old_item in enumerate(belt_before_loop):
                if old_item.name == name:
                    break
            else:
                raise ValueError(f'Unreachable')
            if new_item.is_signed != old_item.is_signed:
                raise ValueError(
                    f'Invalid loop: Incompatible signs, old item {"is" if old_item.is_signed else "is not"} signed, '
                    f'but new item {"is" if new_item.is_signed else "is not"}.'
                )
            if new_idx != old_idx:
                raise ValueError(
                    f'Invalid loop: loop variable {name} ends up on different belt positions {old_idx} != {new_idx}'
                )
        self._end_scope()
        return [InsLoopSpecified(Block(code))]

    def _handle_if(self, if_block: Tree) -> List[Instruction]:
        condition, then_block, *else_block = if_block.children
        condition_idx, _ = self._get_item(condition, False)
        old_belt = self._belt.copy()
        self._begin_scope(None)
        then_code = self._handle_statements(then_block.children)
        self._end_scope()
        if else_block:
            other_belt = self._belt.copy()
            self._belt = old_belt
            else_block, = else_block
            self._begin_scope(None)
            else_code = self._handle_statements(else_block.children)
            self._end_scope()
        else:
            other_belt = old_belt
            else_code = []
        for idx, (other_item, belt_item) in enumerate(zip_longest(other_belt, self._belt,
                                                                  fillvalue=CompilerBeltItem(..., None, False, False))):
            if not other_item.is_consistent or not belt_item.is_consistent or \
                    other_item.name != belt_item.name or \
                    other_item.is_signed != belt_item.is_signed or \
                    other_item.is_slice != belt_item.is_slice:
                self._belt[idx] = CompilerBeltItem(
                    belt_item.name,
                    belt_item.is_signed,
                    belt_item.is_slice,
                    False,
                    other_item,
                )
        return [InsIfUnspecified(condition_idx, Block(then_code), Block(else_code))]

    def _handle_assign(self, assign: Tree) -> List[Instruction]:
        target, expr = assign.children
        names = [name.children[0] for name in target.children]
        return self._handle_expr(names, expr)

    def _handle_call_stmt(self, call_stmt: Tree) -> List[Instruction]:
        call_name, params = call_stmt.children[0].children
        params = params.children
        if call_name == 'unreachable':
            if params:
                raise ValueError('unreachable takes no arguments')
            return [InsUnreachable()]
        elif call_name == 'nop':
            if params:
                raise ValueError('nop takes no arguments')
            return [InsNop()]
        elif call_name in {'br', 'br_if', 'continue'}:
            if call_name in {'br', 'continue'}:
                if len(params) > 1:
                    raise ValueError(f'{call_name} takes at most 1 argument')
                if params:
                    scope_name, = params
                else:
                    scope_name = None
                condition_name = None
            else:
                if len(params) not in {1, 2}:
                    raise ValueError('br_if takes only 1 or 2 arguments')
                if len(params) == 2:
                    condition_name, scope_name = params
                else:
                    condition_name, = params
                    scope_name = None
            br_depth = 1
            if scope_name is not None:
                scope_name, = params
                for idx, scope in enumerate(reversed(self._scopes)):
                    if scope.scope_name == scope_name:
                        br_depth = idx + 1
                        break
                else:
                    raise ValueError(f"Scope {scope_name} not defined")
            if condition_name is not None:
                condition_idx, _ = self._get_item(condition_name, False)
                return [InsBrIf(condition_idx, br_depth)]
            elif call_name == 'br':
                return [InsBr(br_depth)]
            elif call_name == 'continue':
                return [InsBrContinue(br_depth)]
        elif call_name == 'verify':
            if len(params) != 1:
                raise ValueError(f'{call_name} takes exactly 1 argument')
            item_name, = params
            item_idx, _ = self._get_item(item_name, False)
            return [InsVerify(item_idx)]
        elif call_name == 'verify_ok':
            if len(params) != 1:
                raise ValueError(f'{call_name} takes exactly 1 argument')
            item_name, = params
            item_idx, _ = self._get_item(item_name, False)
            return [InsVerifyOk(item_idx)]
        elif call_name == 'verify_eq':
            if len(params) != 2:
                raise ValueError(f'{call_name} takes exactly 2 arguments')
            a_name, b_name = params
            a_idx, a = self._get_item(a_name, False)
            b_idx, b = self._get_item(b_name, False)
            if a.is_signed != b.is_signed:
                raise ValueError(
                    f'Incompatible operands, {a_name} {"is" if a.is_signed else "is not"} signed, '
                    f'but {b_name} {"is" if b.is_signed else "is not"}.'
                )
            return [InsRelVerify(a_idx, b_idx, a.is_signed, lambda x, y: x == y)]
        else:
            raise ValueError(f'Unknown call statement: {call_name}')

    def _handle_store(self, store: Tree) -> List[Instruction]:
        target_name, offset_lit, value_name = store.children
        target_idx, _ = self._get_item(target_name, True)
        offset = int(offset_lit)
        value_idx, _ = self._get_item(value_name, False)
        return [InsStore(value_idx, target_idx, offset)]

    def _handle_load(self, load: Tree) -> List[Instruction]:
        target_name, source_name, offset_lit, type_name = load.children
        source_idx, _ = self._get_item(source_name, True)
        offset = int(offset_lit)
        type_match = self.REG_TYPE.match(type_name)
        is_signed = type_match.group(1) == 'i'
        bit_size = int(type_match.group(2))
        self._push(CompilerBeltItem(target_name, is_signed, False))
        return [InsLoad(DataType(bit_size), source_idx, offset)]

    def _handle_expr(self, names: List[str], expr: Tree) -> List[Instruction]:
        expr, = expr.children
        if expr.data == 'lit':
            return self._handle_lit(names, expr)
        elif expr.data == 'name':
            return self._handle_name(names, expr)
        elif expr.data == 'call':
            return self._handle_call(names, expr)
        elif expr.data == 'operation':
            return self._handle_operation(names, expr)
        elif expr.data == 'slicing':
            return self._handle_slicing(names, expr)
        else:
            raise ValueError(f"Unexpected expr {expr}")

    def _handle_lit(self, names: List[str], lit: Tree) -> List[Instruction]:
        assigned_name, = names
        lit, = lit.children
        lit = lit.replace('_', '')
        if assigned_name.startswith('$'):
            raise ValueError('Cannot assign literals to locals (yet?)')
        m = self.REG_LIT.match(lit)
        num = int(m.group(1))
        is_signed = m.group(2) == 'i'
        bit_size = int(m.group(3))
        self._push(CompilerBeltItem(assigned_name, is_signed, False))
        return [InsConst(BeltNum.from_signed(Integer(num), DataType(bit_size), is_signed))]

    def _handle_name(self, names: List[str], name: Tree) -> List[Instruction]:
        assigned_name, = names
        source_name, = name.children
        if assigned_name.startswith('$'):
            if source_name.startswith('$'):
                raise ValueError('Can only assign belt items to locals, not local to local')
            self._get_item(source_name)
            front = self._belt[0]
            if front.name != source_name:
                raise ValueError(f'Can only assign the front belt ({front.name}) item to a local, got {source_name}')
            local = self._locals.setdefault(assigned_name, CompilerLocal(front.is_signed, front.is_slice, len(self._locals)))
            return [InsLocalSet(local.local_idx)]
        else:
            if not source_name.startswith('$'):
                raise ValueError('Can only assign locals to belt items, not belt item to belt item (yet?)')
            local = self._locals.get(source_name, None)
            if local is None:
                raise ValueError(f'Local {source_name} not defined')
            self._push(CompilerBeltItem(assigned_name, local.is_signed, local.is_slice))
            return [InsLocalGet(local.local_idx)]

    def _handle_call(self, names: List[str], call: Tree) -> List[Instruction]:
        call_name, params = call.children
        params = params.children
        if call_name == 'is_err':
            if len(params) != 1:
                raise ValueError(f'{call_name} takes exactly 1 argument')
            item_name, = params
            result_name, = names
            item_idx, item = self._get_item(item_name, False)
            self._push(CompilerBeltItem(result_name, False, False))
            return [InsIsErr(item_idx)]
        elif call_name == 'length':
            if len(params) != 1:
                raise ValueError(f'{call_name} takes exactly 1 argument')
            slice_name, = params
            result_name, = names
            slice_idx, _ = self._get_item(slice_name, True)
            self._push(CompilerBeltItem(result_name, False, False))
            return [InsSliceLen(slice_idx)]
        elif call_name in {'trim_l', 'trim_r', 'shrink'}:
            if len(params) != 2:
                raise ValueError(f'{call_name} takes exactly 2 argument')
            slice_name, num_bytes_name = params
            result_name, = names
            slice_idx, _ = self._get_item(slice_name, True)
            num_bytes_idx, _ = self._get_item(num_bytes_name, False)
            self._push(CompilerBeltItem(result_name, None, True))
            return [InsSliceOp(slice_idx, num_bytes_idx, {
                'trim_l': BeltSlice.trim_l,
                'trim_r': BeltSlice.trim_r,
                'shrink': BeltSlice.shrink,
            }[call_name])]
        elif call_name == 'divmod':
            if len(params) != 2:
                raise ValueError(f'{call_name} takes exactly 2 argument')
            a_name, b_name = params
            div_name, mod_name = names
            a_idx, a = self._get_item(a_name, False)
            b_idx, b = self._get_item(b_name, False)
            if a.is_signed != b.is_signed:
                raise ValueError(
                    f'Incompatible operands, {a_name} {"is" if a.is_signed else "is not"} signed, '
                    f'but {b_name} {"is" if b.is_signed else "is not"}.')
            self._push(CompilerBeltItem(div_name, a.is_signed, False))
            self._push(CompilerBeltItem(mod_name, a.is_signed, False))
            return [InsNAryOp([a_idx, b_idx], a.is_signed, lambda _, x, y: [None, None] if y == 0 else divmod(x, y))]
        elif call_name in {'rotl', 'rotr', 'clz', 'ctz', 'popcnt'}:
            raise NotImplemented
        else:
            match_cast = self.REG_CAST.match(call_name)
            if match_cast is not None:
                call_name = match_cast.group(1)
                bit_size = int(match_cast.group(2))
                data_type = DataType(bit_size)
                item_name, = params
                result, = names
                item_idx, item = self._get_item(item_name, False)
                self._push(CompilerBeltItem(result, item.is_signed, False))
                if call_name == 'cast_extend':
                    if bit_size == 8:
                        raise ValueError("Cannot use cast_extend8")
                    func = BeltNum.extend
                elif call_name == 'cast_wrap':
                    def func(num: BeltNum, _data_type: DataType, _: bool) -> BeltNum:
                        return num.wrap(_data_type)
                    if bit_size == 64:
                        raise ValueError("Cannot use cast_wrap8")
                elif call_name == 'cast_sat':
                    if bit_size == 64:
                        raise ValueError("Cannot use cast_sat8")
                    func = BeltNum.cast_sat
                elif call_name == 'cast_checked':
                    if bit_size == 64:
                        raise ValueError("Cannot use cast_checked8")
                    func = BeltNum.cast_checked
                else:
                    raise ValueError('Unreachable')
                return [InsConvert(item_idx, data_type, item.is_signed, func)]
            else:
                raise ValueError(f"Unknown function {call_name}")

    def _handle_operation(self, names: List[str], operation: Tree) -> List[Instruction]:
        a_name, op, b_name = operation.children
        a_idx, a = self._get_item(a_name, False)
        b_idx, b = self._get_item(b_name, False)
        if a.is_signed != b.is_signed:
            raise ValueError(
                f'Incompatible operands, {a_name} {"is" if a.is_signed else "is not"} signed, '
                f'but {b_name} {"is" if b.is_signed else "is not"}.')
        is_signed = a.is_signed
        if op == '_+_':
            arith_mode, func = ArithMode.WIDENING, int.__add__
        elif op == '_-_':
            arith_mode, func = ArithMode.WIDENING, int.__sub__
        elif op == '_*_':
            arith_mode, func = ArithMode.WIDENING, int.__mul__
        elif op == '+':
            arith_mode, func = ArithMode.CHECKED, int.__add__
        elif op == '-':
            arith_mode, func = ArithMode.CHECKED, int.__sub__
        elif op == '*':
            arith_mode, func = ArithMode.CHECKED, int.__mul__
        elif op == '/':
            arith_mode, func = ArithMode.CHECKED, int.__floordiv__
        elif op == '%':
            arith_mode, func = ArithMode.CHECKED, int.__mod__
        elif op == '<<':
            arith_mode, func = ArithMode.CHECKED, int.__lshift__
        elif op == '>>':
            arith_mode, func = ArithMode.CHECKED, int.__rshift__
        elif op == '&':
            arith_mode, func = ArithMode.CHECKED, int.__and__
        elif op == '|':
            arith_mode, func = ArithMode.CHECKED, int.__or__
        elif op == '^':
            arith_mode, func = ArithMode.CHECKED, int.__xor__
        elif op == '==':
            arith_mode, func = None, int.__eq__
        elif op == '!=':
            arith_mode, func = None, int.__ne__
        elif op == '<':
            arith_mode, func = None, int.__lt__
        elif op == '<=':
            arith_mode, func = None, int.__le__
        elif op == '>':
            arith_mode, func = None, int.__gt__
        elif op == '>=':
            arith_mode, func = None, int.__ge__
        else:
            raise ValueError(f'Unexpected operator {op}')
        if arith_mode is None:
            name, = names
            self._push(CompilerBeltItem(name, is_signed, False))
            return [InsRel(a_idx, b_idx, is_signed, func)]
        elif arith_mode == ArithMode.WIDENING:
            result_a, result_b = names
            self._push(CompilerBeltItem(result_b, is_signed, False))
            self._push(CompilerBeltItem(result_a, is_signed, False))
        elif arith_mode == ArithMode.CHECKED:
            result, = names
            self._push(CompilerBeltItem(result, is_signed, False))
        return [InsArith([a_idx, b_idx], is_signed, arith_mode, func)]

    def _handle_slicing(self, names: List[str], slicing: Tree) -> List[Instruction]:
        slice_name, *rest = slicing.children
        start_name = rest[0] if rest[0] != '..' else None
        length_name = rest[-1] if rest[-1] != '..' else None
        result, = names
        self._push(CompilerBeltItem(result, None, True))
        if start_name is None and length_name is None:
            raise ValueError('At least either start or length must be given for slice')
        elif start_name is not None and length_name is not None:
            slice_idx, _ = self._get_item(slice_name, True)
            start_idx, _ = self._get_item(start_name, False)
            length_idx, _ = self._get_item(length_name, False)
            return [InsSubSlice(slice_idx, start_idx, length_idx)]
        elif start_name is not None:
            slice_idx, _ = self._get_item(slice_name, True)
            start_idx, _ = self._get_item(start_name, False)
            return [InsSliceOp(slice_idx, start_idx, BeltSlice.trim_l)]
        elif length_name is not None:
            slice_idx, _ = self._get_item(slice_name, True)
            length_idx, _ = self._get_item(start_name, False)
            return [InsSliceOp(slice_idx, length_idx, BeltSlice.shrink)]
        else:
            raise ValueError('Unreachable')


if __name__ == "__main__":
    def main():
        p = Compiler()
        code = p.compile("""
            version 0.0.1;
            a = 3i32;
            b = 2i32;
            c = 1i8;
            if c {
                a = a + b;
                b = a + c;
                c = 1i8;
            }
            x = a + b;
        """)
        print(p._belt)
        print(code)
    main()
