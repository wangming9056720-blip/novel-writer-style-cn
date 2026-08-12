# 拆书词库

本目录用于开发“整本网络小说 → 高召回词库 → 多书通用词库”的自研流程，同时保留参考项目作为架构对照。

## 当前自研 V2

### 总控

- `agents/vocabulary-pipeline-agent.md`：总控 Agent，按批次调度取词、查漏、清洗，并维护 STATE。

### 子 Agent

- `agents/vocabulary-extractor-agent.md`：高召回取词。先多收，不提前按频率或通用性删词。
- `agents/vocabulary-coverage-auditor.md`：只负责找遗漏；用于防止“跑完了但其实漏很多”的假完成。
- `agents/vocabulary-cleaner-agent.md`：清洗短语、错误切词、标题污染；专名和题材词优先隔离而不是静默删除。

### Schema

- `schemas/vocabulary-record.schema.json`：统一词条结构。
- `schemas/vocabulary-state.schema.json`：断点续跑状态结构。

### 流程

- `PIPELINE_V2.md`：整本书从章节解析、批次提取、Coverage 门控、清洗、统计、全书 QA 到多书交叉评级的完整流程。

V2 核心原则：

```text
先召回，再清洗
LLM 发现，程序计数
每词有证据
每批有 Coverage 门控
每批保存 STATE
整本 QA 后才能封版
```

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

自研部分只吸收架构思想，不直接把参考 Fork 的 GPL 源码复制进本仓库。

## 子模块使用

```bash
git clone --recurse-submodules <repo-url>
git submodule update --init --recursive
```

## 许可证说明

两个参考项目以 Git Submodule 形式挂载，保留原仓库、提交历史和各自许可证；它们不因本仓库的 MIT License 被重新许可。
