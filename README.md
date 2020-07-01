# mitra-lab

Read this first:

* Intro article to the idea: https://read.cash/@TobiasRuck/why-mises-would-love-mitra-bitcoin-cashs-hidden-superpower-that-even-ethereum-20-doesnt-have-0e6090bb
* Video on the idea: https://www.youtube.com/watch?v=vI2JecWwYiA
* VM explanation: https://bitcoincashresearch.org/t/mitra-vm-thoughts-on-the-architecture-instruction-set/51/2
* VM & instruction set: https://docs.google.com/spreadsheets/d/10PVUGoOB-otUXvFLbDr3z2R6bPzjVhFqIhdlJlO-Fak/edit

## Usage

This isn‘t really usable right now, but you can already write CashAssembly programs and execute them, although it‘s so cumbersome I can‘t recommend it for anything, even playing around.

The code is not really documented.

```python
from lang.parse import Compiler
from vm import VM
from loop_stack import LoopStack
from op import Block

compiler = Compiler()
result = compiler.compile("""
    version 0.0.1;
    a = 3i32;  # pushes signed 32-bit number named "a" onto the belt
    b = 2i32;  # pushes signed 32-bit number named "b" onto the belt
    c = 1i8;   # pushes signed 8-bit number named "c" onto the belt
    if c {
        a = a + b;  # doesn't consume a and b
        b = a + c;
        c = 1i8;  # push dummy value to keep belt consistent
    }
    x = a + b;
""")

vm = VM(loop_stack=LoopStack([]), num_locals=result.num_locals, ram_size=0)
block = Block(result.instructions)

block.run(vm)  # currently also prints a trace

print(vm.belt())
```
