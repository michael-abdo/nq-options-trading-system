#!/usr/bin/env python3
"""
Chrome Connection Manager for persistent remote debugging connections
Maintains a single connection to Chrome and reuses it across multiple scraping sessions
"""

import asyncio
import logging
from typing import Optional
from pyppeteer import connect

logger = logging.getLogger(__name__)

class ChromeConnectionManager:
    """Singleton manager for Chrome remote debugging connections"""
    
    _instance = None
    _browser = None
    _port = 9222
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_browser(self, port: int = 9222):
        """Get or create browser connection"""
        self._port = port
        
        # Check if we have an active connection
        if self._browser:
            try:
                # Test if connection is still alive
                version = await self._browser.version()
                logger.debug(f"Existing Chrome connection is active: {version}")
                return self._browser
            except Exception as e:
                logger.warning(f"Existing connection failed: {e}")
                self._browser = None
        
        # Create new connection
        try:
            browser_url = f"http://localhost:{self._port}"
            logger.info(f"Connecting to Chrome at {browser_url}")
            self._browser = await connect(browserURL=browser_url)
            version = await self._browser.version()
            logger.info(f"Connected to Chrome: {version}")
            return self._browser
        except Exception as e:
            logger.error(f"Failed to connect to Chrome on port {self._port}: {e}")
            raise
    
    async def get_new_page(self):
        """Get a new page from the connected browser"""
        if not self._browser:
            raise Exception("No browser connection available")
        
        page = await self._browser.newPage()
        
        # Configure page
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # Hide automation
        await page.evaluateOnNewDocument('''() => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        }''')
        
        return page
    
    async def close_page(self, page):
        """Close a page but keep browser connection"""
        if page:
            try:
                await page.close()
                logger.debug("Page closed")
            except Exception as e:
                logger.warning(f"Error closing page: {e}")
    
    def disconnect(self):
        """Disconnect from browser (but don't close it)"""
        if self._browser:
            try:
                asyncio.create_task(self._browser.disconnect())
                logger.info("Disconnected from Chrome (browser still running)")
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
            finally:
                self._browser = None


# Global instance
_connection_manager = ChromeConnectionManager()


async def get_chrome_page(port: int = 9222):
    """Get a new page from persistent Chrome connection"""
    browser = await _connection_manager.get_browser(port)
    page = await _connection_manager.get_new_page()
    return page


async def close_chrome_page(page):
    """Close page but keep Chrome running"""
    await _connection_manager.close_page(page)


def disconnect_from_chrome():
    """Disconnect from Chrome but keep it running"""
    _connection_manager.disconnect()