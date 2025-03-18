from backend.infrastructure.automation_agent.base import AutomationAgent
from backend.infrastructure.enhanced_browser.factory import BrowserProviderType, EnhancedBrowserFactory


class VisionAutomationAgent(AutomationAgent):
    def __init__(self):
        self.browser = EnhancedBrowserFactory.create(BrowserProviderType.SELENIUM)
        self.element_mapping = {}
