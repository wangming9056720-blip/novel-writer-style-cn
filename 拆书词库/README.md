# 拆书词库

本目录用于汇总“拆书 / 提示词 / 长文本分析 / 文风提取”相关参考实现，后续在这里开发自己的番茄网文拆书词库流程。

## reference-forks

### zhuRuan-webnovel-writer-opencode
固定版本：`a2275a698eaaa39db8923a3f4bb3b9c365da0ef0`

重点研究：
- `.opencode/dashboard/services/chapter_splitter.py`：长文本章节切分
- `.opencode/dashboard/services/style_analyzer.py`：逐章文风分析
- `.opencode/dashboard/services/style_summarizer.py`：跨章节文风汇总
- `.opencode/skills/webnovel-write/SKILL.md`：Agent / Skill / 技法检索与提示词注入
- `.opencode/agents/deconstruction-agent.md`：拆书 Agent 基线
- `.opencode/scripts/data_modules/observer_settler.py`：结构化事实提取与高召回思路

用途：主要借鉴批处理、长文本分析、高召回提取、文风/技法统计和持久化流程。

### Saemer2023-webnovel-writer-opencode
固定版本：`900d379d9ffbe54b2e786d0a91ec3d4ce9cc6561`

重点研究：
- `.opencode/agents/deconstruction-agent.md`：拆书提示词与结构化输出
- `.opencode/skills/webnovel-init/SKILL.md`：拆书结果如何进入初始化流程
- `.opencode/scripts/data_modules/tests/test_prompt_integrity.py`：提示词完整性检查
- `.opencode/references/`：题材规则、约束与写作参考

用途：主要借鉴拆书 Agent、Prompt 组织、Skill/Agent 编排和提示词质量控制。

## 上游对照

当前原仓：`lujih/webnovel-writer-opencode`

后续开发自己的流程时，以原仓当前版本作为基线，对两个 Fork 的独立改动逐项吸收，不直接整仓照搬。

## 子模块使用

克隆时：

```bash
git clone --recurse-submodules <repo-url>
```

已有仓库更新子模块：

```bash
git submodule update --init --recursive
```

## 许可证说明

两个参考项目以 Git Submodule 形式挂载，保留原仓库、提交历史和各自许可证；它们不因本仓库的 MIT License 被重新许可。
