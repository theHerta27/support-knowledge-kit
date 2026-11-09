# 客户端配置

先按 README 安装项目。以下路径都是示例，请替换成自己的安装目录；客户端应使用虚拟环境中 Python 的绝对路径。服务和客户端要在同一台机器上运行。

## 通用 stdio JSON

适用于支持 `mcpServers` 配置的客户端。示例使用 Windows 路径，JSON 中用 `/` 可减少转义：

```json
{
  "mcpServers": {
    "support-knowledge": {
      "command": "D:/projects/support-knowledge-kit/.venv/Scripts/python.exe",
      "args": ["-m", "support_knowledge.server"]
    }
  }
}
```

默认使用演示资料。使用自己的资料时，把 `args` 换成：

```json
["-m", "support_knowledge.server", "--kb", "D:/knowledge/support"]
```

macOS / Linux 把 `command` 改为 `/absolute/path/support-knowledge-kit/.venv/bin/python`。不要把整条命令写进 `command` 字段，也不需要先另开终端启动 stdio 服务。

## Claude Code

添加本地服务，下面是一条完整命令：

```powershell
claude mcp add --transport stdio support-knowledge -- "D:/projects/support-knowledge-kit/.venv/Scripts/python.exe" -m support_knowledge.server
```

随后用 `claude mcp get support-knowledge` 查看配置，在会话中用 `/mcp` 检查连接。命令默认写入当前项目的本地配置范围；团队共享配置可按官方文档选择项目范围。

把本仓库的 `skills/support-reply` 整个目录复制到使用项目的 `.claude/skills/support-reply`，或个人目录 `~/.claude/skills/support-reply`。在 Claude Code 中输入：

```text
/support-reply 客户要从广州搬到佛山，请根据资料起草回复。
```

官方参考：[MCP 接入](https://code.claude.com/docs/en/mcp)、[Skill 目录与调用](https://code.claude.com/docs/en/skills)。

## Codex

通过 CLI 添加服务：

```powershell
codex mcp add support-knowledge -- "D:/projects/support-knowledge-kit/.venv/Scripts/python.exe" -m support_knowledge.server
```

也可以在自己的 Codex 配置文件中添加对应 TOML，二选一即可：

```toml
[mcp_servers.support-knowledge]
command = "D:/projects/support-knowledge-kit/.venv/Scripts/python.exe"
args = ["-m", "support_knowledge.server"]
```

把 `skills/support-reply` 复制到使用项目的 `.agents/skills/support-reply`，或个人目录 `~/.agents/skills/support-reply`。在会话中选择该 Skill，或输入：

```text
$support-reply 客户要从广州搬到佛山，请根据资料起草回复。
```

默认发现机制以客户端版本为准；未出现时重新打开会话并检查 Skill 目录。`agents/openai.yaml` 只是可选的界面元数据，不会替你安装 MCP 服务。

官方参考：[MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)、[Skill 目录](https://learn.chatgpt.com/docs/build-skills)。

## 本机 HTTP

在项目虚拟环境中启动：

```bash
python -m support_knowledge.server --transport http --port 8769
```

然后把支持 Streamable HTTP 的客户端指向 `http://127.0.0.1:8769/mcp`。例如：

```bash
codex mcp add support-knowledge-http --url http://127.0.0.1:8769/mcp
```

这个模式只用于同机接入，不含远程鉴权。通常选择 stdio 或 HTTP 其中一种即可，不必重复添加同一份知识库。

## 检查接入是否成功

1. 客户端能列出 `search_knowledge` 与 `read_source`。工具可能带服务名前缀。
2. 搜索“宽带 跨城市 移机”，得到来源 ID 和行范围。
3. 用返回的 ID 读取原文，核对内容和版本。
4. 再调用 Skill 起草回复；只有工具连接而没有安装 Skill，也可以查询，但不会自动获得本项目规定的回复格式。

本页提供按官方文档编写的配置示例。项目测试使用 SDK 客户端检验协议；各 AI 客户端的最终加载情况，请通过以上四步在自己的版本中确认。
