"""Exercise a real stdio MCP server. No model API or API key is used."""

import asyncio
import json
import sys

from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def run_demo() -> dict:
    params = StdioServerParameters(command=sys.executable, args=['-m', 'support_knowledge.server'])
    async with Client(params, read_timeout_seconds=15) as client:
        tools = (await client.list_tools()).tools
        search = await client.call_tool('search_knowledge', {'query': '广州搬到佛山宽带迁移', 'limit': 3})
        if search.is_error:
            raise RuntimeError('MCP search failed')
        hit = search.structured_content['matches'][0]
        source = await client.call_tool('read_source', {
            'source_id': hit['source_id'], 'start_line': hit['start_line'], 'max_lines': 40})
        no_match = await client.call_tool('search_knowledge', {'query': '火星火箭燃料'})
        clarify = await client.call_tool('search_knowledge', {'query': '搬家移机'})
        if any(result.is_error for result in (source, no_match, clarify)):
            raise RuntimeError('MCP demo tool call failed')
        return {
            'transport': 'stdio',
            'tools': [tool.name for tool in tools],
            'normal': {'question': '广州搬到佛山宽带能迁过去吗？',
                       'search': search.structured_content, 'source': source.structured_content},
            'needs_clarification': {'question': '我要搬家，宽带怎么办？',
                                    'search': clarify.structured_content,
                                    'note': '工具只查资料；由 Skill 指导 AI 追问迁出和迁入城市。'},
            'not_found': no_match.structured_content,
            'note': '真实 MCP 协议调用记录；不是大模型回复或准确率评测。样例规则为原创虚构。',
        }


def main() -> None:
    result = asyncio.run(run_demo())
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
