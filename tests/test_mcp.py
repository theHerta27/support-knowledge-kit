import asyncio
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from support_knowledge.server import create_server, default_knowledge_dir


ROOT = Path(__file__).resolve().parents[1]


async def exercise(client):
    tools = (await client.list_tools()).tools
    assert {tool.name for tool in tools} == {'search_knowledge', 'read_source'}
    assert all(tool.annotations.read_only_hint for tool in tools)
    result = await client.call_tool('search_knowledge', {'query': '广州搬到佛山宽带迁移'})
    assert not result.is_error
    hit = result.structured_content['matches'][0]
    assert hit['source_id'] == 'relocation.md'
    source = await client.call_tool('read_source', {
        'source_id': hit['source_id'], 'start_line': hit['start_line']})
    assert not source.is_error
    assert '跨城市不支持' in source.structured_content['content']
    assert hit['version'] == source.structured_content['version']
    no_match = await client.call_tool('search_knowledge', {'query': '火星火箭燃料'})
    assert no_match.structured_content['matches'] == []
    for name, arguments in [
        ('read_source', {'source_id': '../secret.md'}),
        ('search_knowledge', {'query': ''}),
        ('search_knowledge', {'query': '宽带', 'limit': True}),
    ]:
        error = await client.call_tool(name, arguments)
        assert error.is_error


def test_tool_discovery_search_read_and_errors_in_memory():
    async def run():
        async with Client(create_server(default_knowledge_dir())) as client:
            await exercise(client)
    asyncio.run(run())


def test_stdio_protocol_from_another_working_directory(tmp_path):
    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=['-m', 'support_knowledge.server'],
            cwd=tmp_path, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')})
        async with Client(params, read_timeout_seconds=15) as client:
            await exercise(client)
    asyncio.run(run())


def test_http_protocol_on_loopback(tmp_path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    log_path = tmp_path / 'http.log'
    with log_path.open('w', encoding='utf-8') as log:
        process = subprocess.Popen([
            sys.executable, '-m', 'support_knowledge.server', '--transport', 'http', '--port', str(port)],
            env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')}, cwd=tmp_path,
            stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise AssertionError(log_path.read_text(encoding='utf-8'))
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                        break
                except OSError:
                    if time.monotonic() > deadline:
                        raise AssertionError('HTTP server did not start')
                    time.sleep(0.1)
            async def run():
                async with Client(f'http://127.0.0.1:{port}/mcp', read_timeout_seconds=15) as client:
                    await exercise(client)
            asyncio.run(run())
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
