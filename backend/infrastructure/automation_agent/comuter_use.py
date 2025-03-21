import asyncio
import base64
import os
from typing import Literal, Union

from playwright.async_api import Browser, Page, Playwright, async_playwright

from agents import (
    Agent,
    AsyncComputer,
    Button,
    ComputerTool,
    Environment,
    ModelSettings,
    Runner,
    trace,
)

# Uncomment to see very verbose logs
import logging
logging.getLogger("openai.agents").setLevel(logging.DEBUG)
logging.getLogger("openai.agents").addHandler(logging.StreamHandler())


async def main():
    async with LocalPlaywrightComputer() as computer:
        with trace("Computer use example"):
            agent = Agent(
                name="Browser user",
                instructions="You are a helpful agent.",
                tools=[ComputerTool(computer)],
                # Use the computer using model, and set truncation to auto because its required
                model="computer-use-preview",
                model_settings=ModelSettings(truncation="auto"),
            )
            result = await Runner.run(agent, "go to https://app.heysam.ai/ and ask a question about split")
            print(result.final_output)


CUA_KEY_TO_PLAYWRIGHT_KEY = {
    "/": "Divide",
    "\\": "Backslash",
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}


class LocalPlaywrightComputer(AsyncComputer):
    """A computer, implemented using a local Playwright browser."""

    def __init__(self):
        self._playwright: Union[Playwright, None] = None
        self._context: Union[Browser, None] = None  # This will now be a BrowserContext
        self._page: Union[Page, None] = None

    async def __aenter__(self):
        # Start Playwright and call the subclass hook for getting context/page
        self._playwright = await async_playwright().start()
        self._context, self._page = await self._get_browser_and_page(self._playwright)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

    @property
    def context(self) -> Browser:
        assert self._context is not None
        return self._context

    # Replace browser property with context
    @property
    def browser(self) -> Browser:
        # For backward compatibility, returns context
        return self.context

    @property
    def page(self) -> Page:
        assert self._page is not None
        return self._page

    @property
    def environment(self) -> Environment:
        return "browser"

    @property
    def dimensions(self) -> tuple[int, int]:
        return (1024, 768)

    async def screenshot(self) -> str:
        """Capture only the viewport (not full_page)."""
        png_bytes = await self.page.screenshot(full_page=False)
        return base64.b64encode(png_bytes).decode("utf-8")

    async def click(self, x: int, y: int, button: Button = "left") -> None:
        playwright_button: Literal["left", "middle", "right"] = "left"

        # Playwright only supports left, middle, right buttons
        if button in ("left", "right", "middle"):
            playwright_button = button  # type: ignore

        await self.page.mouse.click(x, y, button=playwright_button)

    async def double_click(self, x: int, y: int) -> None:
        await self.page.mouse.dblclick(x, y)

    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        await self.page.mouse.move(x, y)
        await self.page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

    async def type(self, text: str) -> None:
        await self.page.keyboard.type(text)

    async def wait(self) -> None:
        await asyncio.sleep(1)

    async def move(self, x: int, y: int) -> None:
        await self.page.mouse.move(x, y)

    async def keypress(self, keys: list[str]) -> None:
        for key in keys:
            mapped_key = CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key)
            await self.page.keyboard.press(mapped_key)

    async def drag(self, path: list[tuple[int, int]]) -> None:
        if not path:
            return
        await self.page.mouse.move(path[0][0], path[0][1])
        await self.page.mouse.down()
        for px, py in path[1:]:
            await self.page.mouse.move(px, py)
        await self.page.mouse.up()

    async def _get_browser_and_page(self, playwright: Playwright) -> tuple[Browser, Page]:
        width, height = self.dimensions
        launch_args = [
            f"--window-size={width},{height}",
            "--no-first-run",
            "--no-default-browser-check",
            "--password-store=basic",
            "--disable-blink-features=AutomationControlled",
        ]
        
        # Get project path - you might need to adjust this to match your setup
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        raw_data_path = os.path.join(project_root, 'raw_data')
        
        # Set user data directory for browser profile
        user_data_dir = os.path.join(raw_data_path, 'chrome_profile')
        
        # Create the directory if it doesn't exist
        os.makedirs(user_data_dir, exist_ok=True)
        
        # Use persistent context instead of launch + new_context
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=launch_args,
            ignore_default_args=["--enable-automation"],
            viewport={"width": width, "height": height}
        )
        
        # Modify to avoid detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.pages[0]
        if not page:
            page = await context.new_page()
            
        await page.goto("https://app.heysam.ai/")
        # breakpoint()
        return context, page


if __name__ == "__main__":
    asyncio.run(main())
