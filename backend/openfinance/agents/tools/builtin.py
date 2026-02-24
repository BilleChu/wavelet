"""
Built-in Tools for OpenFinance Skills.

_builtin_tools = [
    read_file,
    write_file,
    execute_command,
    web_search,
    web_fetch,
] other tools are prohibitted, because they can do anything

Provides a set of built-in tools for common operations.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from openfinance.agents.tools.decorator import tool, tool_function, register_tool

logger = logging.getLogger(__name__)

_builtin_tools: list[Any] = []


@tool(
    name="read_file",
    description="Read contents from a file",
    parameters={"path": str},
    required=["path"],
    category="filesystem",
)
async def read_file(path: str) -> str:
    """Read file contents.

    Args:
        path: Path to the file.

    Returns:
        File contents as string.
    """
    file_path = Path(path)
    if not file_path.exists():
        return f"Error: File not found: {path}"

    try:
        content = file_path.read_text(encoding="utf-8")
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool(
    name="write_file",
    description="Write content to a file",
    parameters={"path": str, "content": str},
    required=["path", "content"],
    category="filesystem",
    dangerous=True,
)
async def write_file(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: Path to the file.
        content: Content to write.

    Returns:
        Success message or error.
    """
    try:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


# @tool(
#     name="list_directory",
#     description="List contents of a directory",
#     parameters={"path": str},
#     required=["path"],
#     category="filesystem",
# )
# async def list_directory(path: str) -> str:
#     """List directory contents.

#     Args:
#         path: Path to the directory.

#     Returns:
#         Directory listing.
#     """
#     dir_path = Path(path)
#     if not dir_path.exists():
#         return f"Error: Directory not found: {path}"

#     if not dir_path.is_dir():
#         return f"Error: Not a directory: {path}"

#     try:
#         items = []
#         for item in sorted(dir_path.iterdir()):
#             item_type = "DIR" if item.is_dir() else "FILE"
#             size = item.stat().st_size if item.is_file() else "-"
#             items.append(f"{item_type:6} {size:>10} {item.name}")

#         return "\n".join(items)
#     except Exception as e:
#         return f"Error listing directory: {str(e)}"


@tool(
    name="execute_command",
    description="Execute a shell command",
    parameters={"command": str, "timeout": int},
    required=["command"],
    category="shell",
    dangerous=True,
    timeout_seconds=60.0,
)
async def execute_command(command: str, timeout: int = 30) -> str:
    """Execute a shell command.

    Args:
        command: Command to execute.
        timeout: Timeout in seconds.

    Returns:
        Command output.
    """
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout,
        )

        output = []
        if stdout:
            output.append(stdout.decode("utf-8"))
        if stderr:
            output.append(f"STDERR: {stderr.decode('utf-8')}")

        output.append(f"Exit code: {proc.returncode}")

        return "\n".join(output)

    except asyncio.TimeoutError:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool(
    name="web_search",
    description="Search the web for information using Tavily AI",
    parameters={
        "query": str,
        "num_results": int,
        "include_content": bool,
    },
    required=["query"],
    category="web",
)
async def web_search(
    query: str,
    num_results: int = 5,
    include_content: bool = False,
) -> str:
    """Search the web using Tavily AI.

    Args:
        query: Search query.
        num_results: Number of results to return (max 10).
        include_content: Whether to include page content.

    Returns:
        Search results formatted as text.
    """
    import os
    
    api_key = os.getenv("TAVILY_API_KEY")
    
    if not api_key:
        return f"Web search requires TAVILY_API_KEY. Set it in environment variables.\nQuery was: '{query}'"
    
    try:
        from tavily import TavilyClient
        
        client = TavilyClient(api_key=api_key)
        
        response = client.search(
            query=query,
            max_results=min(num_results, 10),
            include_raw_content=include_content,
        )
        
        if not response or "results" not in response:
            return f"No results found for: '{query}'"
        
        results = response["results"]
        
        if not results:
            return f"No results found for: '{query}'"
        
        output_lines = [f"## Search Results for: {query}\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")
            score = result.get("score", 0)
            
            output_lines.append(f"### {i}. {title}")
            output_lines.append(f"URL: {url}")
            output_lines.append(f"Relevance: {score:.2f}")
            
            if content:
                output_lines.append(f"\n{content[:500]}{'...' if len(content) > 500 else ''}")
            
            output_lines.append("")
        
        return "\n".join(output_lines)
        
    except ImportError:
        return f"tavily-python not installed. Run: pip install tavily-python\nQuery was: '{query}'"
    except Exception as e:
        return f"Search error: {str(e)}\nQuery was: '{query}'"


@tool(
    name="web_fetch",
    description="Fetch content from a URL with automatic fallback (aiohttp -> playwright -> tavily)",
    parameters={
        "url": str,
        "method": str,
        "timeout": float,
        "max_retries": int,
    },
    required=["url"],
    category="web",
)
async def web_fetch(
    url: str,
    method: str = "auto",
    timeout: float = 30.0,
    max_retries: int = 3,
) -> str:
    """Fetch content from a URL.

    Supports multiple fetch methods with automatic fallback:
    - aiohttp: Fast static content fetching
    - playwright: Dynamic content (JS-rendered pages)
    - tavily: AI-powered search and extract (fallback)

    Args:
        url: URL to fetch.
        method: Fetch method - "auto", "aiohttp", "playwright", or "tavily".
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries.

    Returns:
        Page content or error message.
    """
    from openfinance.utils.web_fetch import web_fetch as _web_fetch, FetchMethod
    
    method_map = {
        "auto": FetchMethod.AUTO,
        "aiohttp": FetchMethod.AIOHTTP,
        "playwright": FetchMethod.PLAYWRIGHT,
        "tavily": FetchMethod.TAVILY,
    }
    
    fetch_method = method_map.get(method.lower(), FetchMethod.AUTO)
    
    result = await _web_fetch(
        url=url,
        method=fetch_method,
        timeout=timeout,
        max_retries=max_retries,
    )
    
    if result.success:
        if result.title:
            return f"# {result.title}\n\nURL: {result.url}\nMethod: {result.method}\n\n{result.content}"
        return f"URL: {result.url}\nMethod: {result.method}\n\n{result.content}"
    
    return f"Error fetching {url}: {result.error}"


# @tool(
#     name="get_current_time",
#     description="Get the current date and time",
#     parameters={},
#     category="utility",
# )
# async def get_current_time() -> str:
#     """Get current time.

#     Returns:
#         Current date and time.
#     """
#     return datetime.now().isoformat()


# @tool(
#     name="calculate",
#     description="Perform a mathematical calculation",
#     parameters={"expression": str},
#     required=["expression"],
#     category="utility",
# )
# async def calculate(expression: str) -> str:
#     """Calculate a mathematical expression.

#     Args:
#         expression: Mathematical expression to evaluate.

#     Returns:
#         Calculation result.
#     """
#     allowed_chars = set("0123456789+-*/.() ")
#     if not all(c in allowed_chars for c in expression):
#         return "Error: Invalid characters in expression"

#     try:
#         result = eval(expression)
#         return str(result)
#     except Exception as e:
#         return f"Error: {str(e)}"


_builtin_tools = [
    read_file,
    write_file,
    execute_command,
    web_search,
    web_fetch,
]


def register_builtin_tools() -> list[str]:
    """Register all built-in tools.

    Returns:
        List of registered tool names.
    """
    registered = []
    for tool_func in _builtin_tools:
        if hasattr(tool_func, "_tool_name"):
            registered.append(tool_func._tool_name)
    return registered


def get_builtin_tools() -> list[Any]:
    """Get list of built-in tool functions.

    Returns:
        List of tool functions.
    """
    return _builtin_tools.copy()


def get_builtin_tool_names() -> list[str]:
    """Get names of built-in tools.

    Returns:
        List of tool names.
    """
    return [
        tool_func._tool_name
        for tool_func in _builtin_tools
        if hasattr(tool_func, "_tool_name")
    ]
