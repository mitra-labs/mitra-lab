from lang.parse import Compiler
from loop_stack import LoopStack
from loop_tree import parse_loop_trees
from op import Block
from tx import Tx
from vm import VM
import io


def verify_tx(tx: Tx) -> None:
    compiler = Compiler()

    input_sum = sum(sum(outpoint.amount for outpoint in tx_input.outpoints) for tx_input in tx.inputs)
    output_sum = sum(output.amount for output in tx.outputs)

    if output_sum > input_sum:
        raise ValueError('Output amounts exceeds input amounts')

    for input_idx, tx_input in enumerate(tx.inputs):
        witness = tx.witnesses[input_idx]
        loop_trees = parse_loop_trees(io.BytesIO(witness.loop_trees))
        loop_stack = LoopStack(loop_trees)
        src = tx_input.bytecode.decode('ascii')
        compile_result = compiler.compile(src)
        vm = VM(loop_stack, compile_result.num_locals, witness.ram_size)
        instructions = Block(compile_result.instructions)
        instructions.run(vm)

    for preamble_idx, preamble in enumerate(tx.preambles):
        witness = tx.witnesses[len(tx.inputs)+preamble_idx]
        loop_trees = parse_loop_trees(io.BytesIO(witness.loop_trees))
        loop_stack = LoopStack(loop_trees)
        src = preamble.decode('ascii')
        compile_result = compiler.compile(src)
        vm = VM(loop_stack, compile_result.num_locals, witness.ram_size)
        instructions = Block(compile_result.instructions)
        instructions.run(vm)
