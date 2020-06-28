from enum import Enum
from typing import NamedTuple, List


class Tx(NamedTuple):
    inputs: List['Input']
    outputs: List['Output']
    preambles: List[bytes]
    unlock_data: List['UnlockData']
    signatures: List['Signature']


class Input(NamedTuple):
    outpoints: List['Outpoint']
    bytecode_merkle_path: List['MerkleBranch']
    bytecode: bytes


class Output(NamedTuple):
    amount: int
    bytecode_merkle_root: bytes


class UnlockData(NamedTuple):
    data: List[bytes]
    loop_trees: bytes
    ram_size: int


class Signature(NamedTuple):
    sig_flags: int
    num_covered_checks: int
    signature: bytes


class Outpoint(NamedTuple):
    tx_hash: bytes
    idx: int
    amount: int
    constraints: List
    carryover: bytes


class MerkleBranch(NamedTuple):
    side: 'MerkleSide'
    branch_hash: bytes


class MerkleSide(Enum):
    LEFT = 1
    RIGHT = 2


class Constraint(NamedTuple):
    constraint_type: 'ConstraintType'
    payload: bytes


class ConstraintType(Enum):
    PREAMBLE_HASH = 1
    PREAMBLES_HASH = 2
    BLOCK_HEIGHT = 3
    BLOCK_HASH = 4
    AGE = 5
    TIMESTAMP = 6
