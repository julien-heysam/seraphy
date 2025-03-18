from enum import Enum
from typing import Optional

from backend.infrastructure.automation_agent.base import AutomationAgent
from backend.infrastructure.automation_agent.vision import VisionAutomationAgent
from backend.infrastructure.factory import FactoryError


class AutomationAgentType(Enum):
    VISION = "vision"


class AutomationAgentFactory:
    REQUIRED_PARAMS: dict[AutomationAgentType, set[str]] = {AutomationAgentType.VISION: set()}

    @classmethod
    def validate_params(cls, provider_type: AutomationAgentType, params: dict) -> None:
        required_params = cls.REQUIRED_PARAMS[provider_type]
        missing_params = required_params - set(params.keys())
        
        if missing_params:
            raise ValueError(
                f"Missing required parameters for {provider_type.value}: {', '.join(missing_params)}"
            )
        
    @classmethod
    def create(cls, provider_type: AutomationAgentType, **kwargs) -> Optional[AutomationAgent]:
        if not isinstance(provider_type, AutomationAgentType):
            raise ValueError(f"Invalid provider type. Must be one of: {[t.value for t in AutomationAgentType]}")

        cls.validate_params(provider_type, kwargs)
        if provider_type == AutomationAgentType.VISION:
            return VisionAutomationAgent()
        raise FactoryError(f"No factory registered for provider type '{provider_type}'")
