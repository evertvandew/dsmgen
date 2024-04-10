#!/usr/bin/env python3
"""
This file fills the library part of the block_programming database.

"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum, IntEnum


class Dir(Enum):
    input = 'input'
    output = 'output'

class PT(Enum):
    sync = 'sync'
    event = 'async'
    config = 'config'

@dataclass
class PD:
    direction: Dir
    type: PT
    protocol: str

@dataclass
class BD:
    parameters: Dict[str, type]
    ports: Dict[str, PD]
    python_code: Optional[str]
    rust_code: Optional[str]
    arduino_code: Optional[str]



timer_blocks = {
    'RepeatingTick': BD({'frequency': float}, {'config': PD(Dir.input, type: PT.config, )})
}



