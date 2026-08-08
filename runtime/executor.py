"""Executor——控制循环上限和中断条件。"""
from dataclasses import dataclass

from runtime.state import AgentState


@dataclass
class ExecutorConfig:
    max_turns: int = 5


class Executor:
    def __init__(self, config: ExecutorConfig):
        self.config = config

    def should_stop(self, state: AgentState) -> bool:
        return state.turn_count >= self.config.max_turns
