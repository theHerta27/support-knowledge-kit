# Third-party notices

Support Knowledge Kit 的实现、Skill 正文和虚构示例资料为本项目编写，采用仓库中的 Apache-2.0 许可证。本文件列出开发中参考的公开项目；不表示这些项目或其作者为本项目提供背书。

## 运行依赖

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)：MIT License。负责 MCP 协议、服务端工具登记和客户端调用。
- [PyYAML](https://github.com/yaml/pyyaml)：MIT License。负责读取 Markdown 文件头的 YAML 元数据。

依赖通过包管理器安装，保留其各自发行包中的许可证。开发和测试依赖见 `pyproject.toml`。

## 设计参考

- [Anthropic Customer Support Plugin](https://github.com/anthropics/knowledge-work-plugins/tree/main/customer-support)：Apache-2.0。参考客服回复起草时分开组织客户正文与内部事项，以及通过工具查询资料的工作方式。
- [Anthropic webapp-testing Skill](https://github.com/anthropics/skills/tree/main/skills/webapp-testing)：Apache-2.0。参考 `SKILL.md`、可选辅助资源和按需加载的目录组织。
- [Agent Skills specification](https://agentskills.io/specification)：用于核对 Skill 的名称、描述与文件格式。

上述参考项目的原文没有作为本项目的 Skill 正文整段复制。后续贡献者如直接复制或改写第三方文件，应保留其许可和相关声明，并说明修改内容。
