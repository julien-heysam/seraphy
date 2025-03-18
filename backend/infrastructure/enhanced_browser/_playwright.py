from abc import ABC, abstractmethod

class PlaywrightEnhancedBrowser(ABC):
    @abstractmethod
    def navigate_to(self, url: str) -> None:
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        pass
    
    @abstractmethod
    def run(self) -> None:
        pass
