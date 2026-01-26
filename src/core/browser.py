"""
Browser Automation Tool for CursorBot
Inspired by ClawdBot's browser capabilities

Provides:
- Headless browser control
- Web scraping
- Screenshot capture
- Form automation
"""

import asyncio
import base64
from dataclasses import dataclass
from typing import Any, Optional

from ..utils.logger import logger

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Browser, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None


@dataclass
class BrowserResult:
    """Result from browser operation."""
    success: bool
    data: Any = None
    screenshot: Optional[bytes] = None
    error: Optional[str] = None


class BrowserTool:
    """
    Browser automation tool using Playwright.
    
    Usage:
        browser = BrowserTool()
        await browser.start()
        
        result = await browser.navigate("https://example.com")
        result = await browser.screenshot()
        result = await browser.get_text("h1")
        
        await browser.stop()
    """

    def __init__(self, headless: bool = True):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("playwright not installed. Run: pip install playwright && playwright install")

        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    @property
    def is_running(self) -> bool:
        return self._browser is not None and self._page is not None

    async def start(self) -> bool:
        """Start the browser."""
        if self.is_running:
            return True

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.headless)
            self._page = await self._browser.new_page()
            logger.info("Browser started")
            return True
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False

    async def stop(self) -> None:
        """Stop the browser."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> BrowserResult:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (domcontentloaded, load, networkidle)
        """
        if not self.is_running:
            await self.start()

        try:
            response = await self._page.goto(url, wait_until=wait_until)
            return BrowserResult(
                success=response.ok if response else True,
                data={
                    "url": self._page.url,
                    "title": await self._page.title(),
                    "status": response.status if response else None,
                }
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def screenshot(
        self,
        full_page: bool = False,
        selector: str = None,
    ) -> BrowserResult:
        """
        Take a screenshot.
        
        Args:
            full_page: Capture full page
            selector: Optional selector to screenshot specific element
        """
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            if selector:
                element = await self._page.query_selector(selector)
                if element:
                    screenshot = await element.screenshot()
                else:
                    return BrowserResult(success=False, error=f"Element not found: {selector}")
            else:
                screenshot = await self._page.screenshot(full_page=full_page)

            return BrowserResult(
                success=True,
                screenshot=screenshot,
                data={"size": len(screenshot)}
            )
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def get_text(self, selector: str = "body") -> BrowserResult:
        """Get text content of an element."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            element = await self._page.query_selector(selector)
            if element:
                text = await element.text_content()
                return BrowserResult(success=True, data=text)
            return BrowserResult(success=False, error=f"Element not found: {selector}")
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def get_html(self, selector: str = "body") -> BrowserResult:
        """Get HTML content of an element."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            element = await self._page.query_selector(selector)
            if element:
                html = await element.inner_html()
                return BrowserResult(success=True, data=html)
            return BrowserResult(success=False, error=f"Element not found: {selector}")
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def click(self, selector: str) -> BrowserResult:
        """Click an element."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            await self._page.click(selector)
            return BrowserResult(success=True)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def fill(self, selector: str, value: str) -> BrowserResult:
        """Fill an input field."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            await self._page.fill(selector, value)
            return BrowserResult(success=True)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def type(self, selector: str, text: str, delay: int = 50) -> BrowserResult:
        """Type text into an element."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            await self._page.type(selector, text, delay=delay)
            return BrowserResult(success=True)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> BrowserResult:
        """Wait for an element to appear."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return BrowserResult(success=True)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def evaluate(self, script: str) -> BrowserResult:
        """Evaluate JavaScript in the page."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            result = await self._page.evaluate(script)
            return BrowserResult(success=True, data=result)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def get_cookies(self) -> BrowserResult:
        """Get all cookies."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            cookies = await self._page.context.cookies()
            return BrowserResult(success=True, data=cookies)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def set_cookies(self, cookies: list[dict]) -> BrowserResult:
        """Set cookies."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            await self._page.context.add_cookies(cookies)
            return BrowserResult(success=True)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))

    async def pdf(self) -> BrowserResult:
        """Generate PDF of the page."""
        if not self.is_running:
            return BrowserResult(success=False, error="Browser not running")

        try:
            pdf_data = await self._page.pdf()
            return BrowserResult(success=True, data=pdf_data)
        except Exception as e:
            return BrowserResult(success=False, error=str(e))


# Global instance
_browser_tool: Optional[BrowserTool] = None


def get_browser_tool() -> Optional[BrowserTool]:
    """Get the global BrowserTool instance."""
    global _browser_tool
    if not PLAYWRIGHT_AVAILABLE:
        return None
    if _browser_tool is None:
        _browser_tool = BrowserTool()
    return _browser_tool


__all__ = ["BrowserTool", "BrowserResult", "get_browser_tool", "PLAYWRIGHT_AVAILABLE"]
