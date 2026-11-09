# Support Knowledge Kit

**把本地客服资料接给 AI 助手，让回复有原文可查、有条件可核对。**

[![tests](https://github.com/theHerta27/support-knowledge-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/theHerta27/support-knowledge-kit/actions/workflows/ci.yml)

[看一条真实演练回复](examples/reply-demo.md) · [读 Skill](skills/support-reply/SKILL.md) · [读 MCP 服务代码](src/support_knowledge/server.py)

这个项目提供两个 MCP 工具和一个 Agent Skill：工具负责搜索、读取 Markdown 资料，Skill 指导 AI 查清规则、起草客户回复，并单独记录依据与待确认事项。适合产品 FAQ、业务规则、排障手册等小型知识库。

```text
客户问题 → 已有 AI 助手读取 support-reply Skill
                     ↓
            搜索资料 → 阅读带行号原文
                     ↓
        客户回复草稿 + 内部依据 + 待确认事项
```

MCP 服务本身不调用大模型，不需要 API Key，也不下载嵌入模型。生成回复由你接入的 AI 客户端完成，相关模型费用按客户端的配置计费。本项目提供工具和工作步骤，不包含独立的聊天网站或企业账户系统。

## 快速开始

需要 Python 3.11 或更高版本。当前固定使用官方 MCP Python SDK 2.3.0。

```bash
git clone https://github.com/theHerta27/support-knowledge-kit.git
cd support-knowledge-kit
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m support_knowledge.demo
```

macOS / Linux：

```bash
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m support_knowledge.demo
```

后文的 `python` 命令也应使用这个虚拟环境中的 Python；可以直接替换为上面的完整路径。

演示会启动 MCP 子进程，通过客户端发现工具、搜索资料并读取原文。它验证工具调用，不生成大模型回复，也不需要密钥。包内资料是原创的**虚构宽带服务示例**，用于理解工作流程，不代表任何真实运营商的规定。

## 接到 AI 客户端

1. 根据 [客户端配置](examples/client-configs.md)，连接本地 MCP 服务。
2. 把 [skills/support-reply](skills/support-reply) 整个目录复制到所用客户端的 Skill 目录。
3. 在客户端确认两个工具可用，并调用 Skill。例如：

```text
使用 support-reply，根据当前知识库起草客服回复：
客户下周从广州搬到佛山，想知道原宽带能不能迁过去。
请给出客户回复，并单独列出资料依据和需要确认的事项。
```

仅克隆仓库不会自动把工具或 Skill 安装进客户端。客户端配置页提供 Codex、Claude Code 和通用 JSON 示例；安装后的权限提示按宿主要求处理。

## 两个工具

| 工具 | 输入 | 返回 |
| --- | --- | --- |
| `search_knowledge` | `query`，可选 `limit` | 相关段落、来源 ID、行号、标题、元数据、版本和检索分数 |
| `read_source` | `source_id`，可选 `start_line`、`max_lines` | 带行号的原文、资料版本、总行数和下一页位置 |

搜索采用 BM25，中文按相邻双字生成词项，英文按单词匹配。它适合快速检索本地文字资料；分数表示词项相关性，不是回答正确率或置信度。AI 应阅读原文后再判断答案是否充分。

## 使用自己的资料

准备一个只放待查询资料的目录，保存 UTF-8 编码的 `.md` 文件。文件开头可以写 YAML 元数据：

```markdown
---
title: 产品迁移说明
scope: 指定产品与地区
updated: "2026-11-09"
---

# 产品迁移说明

## 适用条件

在这里写正式业务规则，并说明例外情况。
```

`title`、`scope`、`updated`、`source_url` 都是可选字段；有真实原始网页时再填写 `source_url`。按标题分节有助于工具返回容易阅读的片段。

在客户端启动参数中加入：

```text
-m support_knowledge.server --kb /absolute/path/to/knowledge
```

使用绝对路径，避免客户端从不同目录启动时找错资料。未指定 `--kb` 时使用包内演示资料。服务在启动时加载资料快照；修改资料后重启服务，搜索与读取才会使用新内容。

### 本机 HTTP 模式

```bash
python -m support_knowledge.server --transport http --port 8769
```

客户端连接 `http://127.0.0.1:8769/mcp`。HTTP 模式只监听本机，没有远程用户鉴权；默认的 stdio 模式更适合本地助手，由客户端启动和管理进程。

## Skill 做了什么

[support-reply/SKILL.md](skills/support-reply/SKILL.md) 写明了几条具体工作要求：

- 按决定结论的条件搜索，例如同城与跨城市移机。
- 读取完整条款，保留文件、行号和版本，能回到原文检查。
- 区分业务规则与个人账户状态，费用和办理结果须有实际依据。
- 资料缺失时指出需要补充什么，而不是把未命中解释为业务不存在。
- 默认分开交付客户回复与客服内部记录；起草不会自动发送消息。

这是一份给模型使用的工作指南，不是硬编码规则引擎。工具参数、文件访问范围和分页由程序检查；回复内容仍需要结合实际业务确认。

## 开发与验证

安装开发依赖后运行：

```bash
python -m pytest
python -m support_knowledge.demo
```

从 [源码导读](docs/learning/walkthrough.md) 开始，按“资料加载 → 搜索 → 读取 → MCP 调用 → Skill”的顺序看。Skill 的人工演练记录见 [验证说明](docs/learning/skill-validation.md)。自动化测试证明的是检索、来源读取和工具协议行为，不代表企业客服回答准确率。

## 开源与参考

采用 [Apache-2.0](LICENSE) 许可。代码、Skill 和演示资料可用于学习和扩展。

项目参考了官方 MCP SDK 的工具注册方式，以及 Anthropic 客服 Skill 的任务组织方式；具体来源与许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本项目未接入任何运营商的真实账单、工单或客户数据。
