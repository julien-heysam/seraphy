from abc import ABC

class AutomationAgent(ABC):

    def __init__(self):
        self.browser = None
        self.element_mapping = {}
