# src/engine/round_phases/base_phase.py
from abc import ABC, abstractmethod
import logging
from typing import Optional

from pydantic import BaseModel, Field

# Direct imports instead of forward references
from src.engine.game_state_manager import GameStateManager
from src.engine.agent_manager import AgentManager
from src.communication.message_dispatcher import MessageDispatcher
from src.engine.scenario_manager import ScenarioManager
from src.agents.referee_agent import RefereeAgent
from src.io.input_handler import UserInputHandler # Import UserInputHandler
# Import GameState only if needed for type hints outside PhaseContext

from src.models.game_state_models import GameState


class PhaseContext(BaseModel):
    """
    上下文对象，用于向回合阶段处理器传递必要的管理器和状态信息。
    """
    game_state_manager: GameStateManager = Field(...) # Direct type hint
    agent_manager: AgentManager = Field(...) # Direct type hint
    message_dispatcher: MessageDispatcher = Field(...) # Direct type hint
    scenario_manager: ScenarioManager = Field(...) # Direct type hint
    referee_agent: RefereeAgent = Field(...) # Direct type hint
    current_round_id: int = Field(...)
    input_handler: Optional[UserInputHandler] = Field(None, description="处理器，用于获取用户输入") # Add input_handler
    # 可以根据需要添加更多字段，例如当前的 GameState 快照

    class Config:
        arbitrary_types_allowed = True # 允许非 Pydantic 类型

class BaseRoundPhase(ABC):
    """
    回合阶段处理器的抽象基类。
    """
    def __init__(self, context: PhaseContext):
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)
        # 子类可以通过 self.context 访问所有管理器
        self.game_state_manager = context.game_state_manager
        self.agent_manager = context.agent_manager
        self.message_dispatcher = context.message_dispatcher
        self.scenario_manager = context.scenario_manager
        self.referee_agent = context.referee_agent
        self.current_round_id = context.current_round_id

    @abstractmethod
    async def execute(self) -> None:
        """
        执行该阶段的核心逻辑。
        子类需要实现此方法。
        """
        pass

    # Keep GameState hint under TYPE_CHECKING if GameState itself might cause issues
    def get_current_state(self) -> 'GameState':
        """辅助方法，获取当前游戏状态"""
        # Assuming get_state() returns the correct type
        return self.game_state_manager.get_state()
