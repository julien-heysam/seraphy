from enum import Enum
from typing import Optional

from backend.infrastructure.enhanced_browser.base import EnhancedBrowser
from backend.infrastructure.enhanced_browser._selenium import SeleniumEnhancedBrowser


class BrowserProviderType(Enum):
    SELENIUM = "selenium"


class EnhancedBrowserFactory:
    REQUIRED_PARAMS: dict[BrowserProviderType, set[str]] = {
        BrowserProviderType.SELENIUM: set(),
    }

    @classmethod
    def validate_params(cls, provider_type: BrowserProviderType, params: dict) -> None:
        required_params = cls.REQUIRED_PARAMS[provider_type]
        missing_params = required_params - set(params.keys())
        
        if missing_params:
            raise ValueError(
                f"Missing required parameters for {provider_type.value}: {', '.join(missing_params)}"
            )
        
    @classmethod
    def create(cls, provider_type: BrowserProviderType, **kwargs) -> Optional[EnhancedBrowser]:
        if not isinstance(provider_type, BrowserProviderType):
            raise ValueError(f"Invalid provider type. Must be one of: {[t.value for t in BrowserProviderType]}")

        cls.validate_params(provider_type, kwargs)
        if provider_type == BrowserProviderType.SELENIUM:
            return SeleniumEnhancedBrowser(chrome_driver_path=kwargs.get("chrome_driver_path"))
        raise FactoryError(f"No factory registered for provider type '{provider_type}'")
