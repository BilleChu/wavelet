"""
Web Fetch Module.

Provides a robust async web fetching function with multiple backends:
- aiohttp: Fast static content fetching
- playwright: Dynamic content (JS-rendered pages)
- tavily: AI-powered search and extract (fallback)

Features:
- Auto-detection of content type
- Automatic fallback between methods
- Retry with exponential backoff
- Request header rotation
- Timeout handling
- Content extraction and cleaning
"""

import asyncio
import logging
import os
import random
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FetchMethod(str, Enum):
    """Available fetch methods."""
    AIOHTTP = "aiohttp"
    PLAYWRIGHT = "playwright"
    TAVILY = "tavily"
    AUTO = "auto"


@dataclass
class FetchResult:
    """Result of a web fetch operation."""
    url: str
    content: str
    title: str | None = None
    method: str = "unknown"
    status_code: int = 200
    error: str | None = None
    metadata: dict[str, Any] | None = None
    
    @property
    def success(self) -> bool:
        return self.error is None and bool(self.content)


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]

DYNAMIC_CONTENT_INDICATORS = [
    "react", "vue", "angular", "spa", "single-page",
    "__NEXT_DATA__", "__NUXT__", "window.__INITIAL_STATE__",
    "requirejs", "webpack", "systemjs",
]

ANTI_BOT_DOMAINS = [
    "cloudflare.com", "datadome.co", "perimeterx.com",
    "akamai.com", "incapsula.com", "distilnetworks.com",
]


def get_random_headers(url: str) -> dict[str, str]:
    """Generate random headers for request."""
    parsed = urlparse(url)
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Host": parsed.netloc,
    }


def clean_html(html: str, url: str) -> tuple[str, str | None]:
    """Clean HTML and extract main content."""
    try:
        soup = BeautifulSoup(html, "lxml")
        
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
            tag.decompose()
        
        for tag in soup.find_all(class_=re.compile(r"(nav|footer|header|sidebar|advertisement|ad-|social|share|comment)", re.I)):
            tag.decompose()
        
        for tag in soup.find_all(id=re.compile(r"(nav|footer|header|sidebar|advertisement|ad-|social|share|comment)", re.I)):
            tag.decompose()
        
        title = None
        if soup.title:
            title = soup.title.get_text(strip=True)
        
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"(content|article|post|entry|main)", re.I))
        
        if main_content:
            text = main_content.get_text(separator="\n", strip=True)
        else:
            body = soup.find("body")
            text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)
        
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
        
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        return text, title
        
    except Exception as e:
        logger.warning(f"HTML cleaning failed: {e}")
        return html, None


def is_dynamic_content(html: str) -> bool:
    """Check if page likely requires JavaScript rendering."""
    html_lower = html.lower()
    
    for indicator in DYNAMIC_CONTENT_INDICATORS:
        if indicator.lower() in html_lower:
            return True
    
    body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.I)
    if body_match:
        body_content = body_match.group(1)
        text_content = re.sub(r"<[^>]+>", "", body_content).strip()
        if len(text_content) < 500 and len(body_content) > 5000:
            return True
    
    return False


def is_anti_bot_domain(url: str) -> bool:
    """Check if domain is known for anti-bot protection."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    for anti_bot in ANTI_BOT_DOMAINS:
        if anti_bot in domain:
            return True
    
    return False


async def fetch_with_aiohttp(
    url: str,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """Fetch URL using aiohttp (for static content)."""
    
    request_headers = headers or get_random_headers(url)
    
    try:
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(url, headers=request_headers, ssl=False) as response:
                status_code = response.status
                
                if status_code != 200:
                    return FetchResult(
                        url=url,
                        content="",
                        status_code=status_code,
                        error=f"HTTP {status_code}",
                        method="aiohttp",
                    )
                
                html = await response.text()
                content, title = clean_html(html, url)
                
                return FetchResult(
                    url=url,
                    content=content,
                    title=title,
                    status_code=status_code,
                    method="aiohttp",
                    metadata={"raw_length": len(html)},
                )
                
    except asyncio.TimeoutError:
        return FetchResult(
            url=url,
            content="",
            error=f"Timeout after {timeout}s",
            method="aiohttp",
        )
    except aiohttp.ClientError as e:
        return FetchResult(
            url=url,
            content="",
            error=f"Client error: {str(e)}",
            method="aiohttp",
        )
    except Exception as e:
        logger.exception(f"aiohttp fetch failed: {e}")
        return FetchResult(
            url=url,
            content="",
            error=f"Unexpected error: {str(e)}",
            method="aiohttp",
        )


async def fetch_with_playwright(
    url: str,
    timeout: float = 60.0,
    wait_time: float = 2.0,
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """Fetch URL using Playwright (for dynamic/JS content)."""
    
    try:
        from playwright.async_api import async_playwright
        
    except ImportError:
        return FetchResult(
            url=url,
            content="",
            error="Playwright not installed. Run: pip install playwright && playwright install",
            method="playwright",
        )
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            
            if headers:
                await context.set_extra_http_headers(headers)
            
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                
                try:
                    await page.wait_for_load_state("networkidle", timeout=min(5000, timeout * 500))
                except Exception:
                    pass
                
                await asyncio.sleep(wait_time)
                
                html = await page.content()
                
                title = await page.title()
                
                await browser.close()
                
                content, extracted_title = clean_html(html, url)
                
                return FetchResult(
                    url=url,
                    content=content,
                    title=extracted_title or title,
                    method="playwright",
                    metadata={"raw_length": len(html)},
                )
                
            except Exception as e:
                await browser.close()
                raise e
                
    except asyncio.TimeoutError:
        return FetchResult(
            url=url,
            content="",
            error=f"Timeout after {timeout}s",
            method="playwright",
        )
    except Exception as e:
        logger.exception(f"Playwright fetch failed: {e}")
        return FetchResult(
            url=url,
            content="",
            error=f"Playwright error: {str(e)}",
            method="playwright",
        )


async def fetch_with_tavily(
    url: str,
    api_key: str | None = None,
) -> FetchResult:
    """Fetch URL using Tavily API (AI-powered extraction)."""
    
    api_key = api_key or os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        return FetchResult(
            url=url,
            content="",
            error="TAVILY_API_KEY not configured",
            method="tavily",
        )
    
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=api_key)
        
        response = client.extract(urls=[url])
        
        if response and "results" in response:
            results = response["results"]
            if results and len(results) > 0:
                result = results[0]
                return FetchResult(
                    url=url,
                    content=result.get("raw_content", ""),
                    title=result.get("title"),
                    method="tavily",
                    metadata={"response": result},
                )
        
        return FetchResult(
            url=url,
            content="",
            error="No content extracted by Tavily",
            method="tavily",
        )
        
    except ImportError:
        return FetchResult(
            url=url,
            content="",
            error="tavily-python not installed. Run: pip install tavily-python",
            method="tavily",
        )
    except Exception as e:
        logger.exception(f"Tavily fetch failed: {e}")
        return FetchResult(
            url=url,
            content="",
            error=f"Tavily error: {str(e)}",
            method="tavily",
        )


async def web_fetch(
    url: str,
    method: FetchMethod = FetchMethod.AUTO,
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    fallback: bool = True,
    clean_content: bool = True,
) -> FetchResult:
    """
    Fetch content from a URL with automatic fallback and retry.
    
    Args:
        url: URL to fetch
        method: Fetch method (aiohttp, playwright, tavily, auto)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries (exponential backoff)
        fallback: Enable automatic fallback between methods
        clean_content: Clean and extract main content from HTML
    
    Returns:
        FetchResult with content and metadata
    
    Example:
        result = await web_fetch("https://example.com")
        if result.success:
            print(result.content)
        else:
            print(f"Error: {result.error}")
    """
    
    if not url:
        return FetchResult(url=url, content="", error="Empty URL")
    
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    methods_to_try = []
    
    if method == FetchMethod.AUTO:
        if is_anti_bot_domain(url):
            methods_to_try = [FetchMethod.TAVILY, FetchMethod.PLAYWRIGHT, FetchMethod.AIOHTTP]
        else:
            methods_to_try = [FetchMethod.AIOHTTP, FetchMethod.PLAYWRIGHT, FetchMethod.TAVILY]
    elif method == FetchMethod.AIOHTTP:
        methods_to_try = [FetchMethod.AIOHTTP]
    elif method == FetchMethod.PLAYWRIGHT:
        methods_to_try = [FetchMethod.PLAYWRIGHT]
    elif method == FetchMethod.TAVILY:
        methods_to_try = [FetchMethod.TAVILY]
    
    if not fallback:
        methods_to_try = methods_to_try[:1]
    
    last_result = None
    
    for current_method in methods_to_try:
        for attempt in range(max_retries):
            logger.debug(f"Fetching {url} with {current_method.value} (attempt {attempt + 1}/{max_retries})")
            
            if current_method == FetchMethod.AIOHTTP:
                result = await fetch_with_aiohttp(url, timeout=timeout)
            elif current_method == FetchMethod.PLAYWRIGHT:
                result = await fetch_with_playwright(url, timeout=timeout * 2)
            elif current_method == FetchMethod.TAVILY:
                result = await fetch_with_tavily(url)
            else:
                continue
            
            last_result = result
            
            if result.success:
                if current_method == FetchMethod.AIOHTTP and is_dynamic_content(result.content):
                    logger.info(f"Detected dynamic content, trying playwright")
                    pw_result = await fetch_with_playwright(url, timeout=timeout * 2)
                    if pw_result.success:
                        return pw_result
                
                return result
            
            if attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)
                logger.debug(f"Retry in {delay}s...")
                await asyncio.sleep(delay)
        
        if fallback and last_result and not last_result.success:
            logger.info(f"Method {current_method.value} failed, trying next method")
    
    return last_result or FetchResult(
        url=url,
        content="",
        error="All fetch methods failed",
    )


async def web_fetch_simple(url: str) -> str:
    """
    Simple web fetch that returns content string.
    
    Args:
        url: URL to fetch
    
    Returns:
        Page content as string, or error message
    """
    result = await web_fetch(url)
    
    if result.success:
        if result.title:
            return f"# {result.title}\n\n{result.content}"
        return result.content
    
    return f"Error fetching {url}: {result.error}"