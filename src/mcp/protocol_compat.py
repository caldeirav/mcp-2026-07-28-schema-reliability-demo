"""Accept MCP 2026-07-28 on FastMCP Streamable HTTP.

The Python MCP SDK still lists 2025-11-25 as latest. agentgateway forwards
``Mcp-Protocol-Version`` to the loopback FastMCP servers; append 2026-07-28
so stateless POSTs are not rejected at the header gate. No session store.
"""

from mcp import types as mcp_types
from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS

MCP_2026 = "2026-07-28"
if MCP_2026 not in SUPPORTED_PROTOCOL_VERSIONS:
    SUPPORTED_PROTOCOL_VERSIONS.append(MCP_2026)
mcp_types.LATEST_PROTOCOL_VERSION = MCP_2026
