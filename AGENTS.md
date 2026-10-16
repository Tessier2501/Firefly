# Firefly 工作区操作规范

Firefly 是 Windows 端的无人设备调试工作区。

## 1. 接手流程
新 agent 在修改工作区之前，必须按顺序完成：

1. 阅读根目录 `AGENTS.md`和 `README.md`。
2. 检查工作树真实状态。
3. 按任务需要阅读目录级规则：
   - `docs/AGENTS.md`（文档检索、硬件资料读取）
   - `scripts/AGENTS.md`（环境和工具用法）
4. 先输出 `HANDOFF BRIEF`，再开始规划或修改。
5. 如记忆与实时证据冲突，以实时证据和当前指令为准；报告过期记忆，并提出 `MEMORY DELTA`。

## 2. 环境与工具



### 3.2 工具清单



规则：

- 任何工具先跑 `--selftest`；有 `--dry-run` 的先 dry-run。
- 对 `docs/hardware/` 的写操作必须经用户确认。
- 工具报错或缺依赖时要显式失败，不要用替代逻辑掩盖。

## 4. 调试与实验纪律

1. **链路边界测量**：定位根因时逐段验证命令、计算输出、串口/电气输出、执行器响应和物理效果；一个边界的正向结果不能替代失败边界的测量。
2. **一次一个变量**：记录旧值、新值、写入者、时间、生效条件、观测效果；没有预期效果先回滚再改下一个变量；批量修改只能作为可回滚的应急操作。
3. **安全门禁**：不得关闭安全、健康或解锁检查来推进调试；在安全台架上重新开启，并以其输出作为阻塞清单。“能解锁/能启动”不是健康指标。
4. **直接探针优先**：组件能独立隔离时，先在组件边界取 ground truth，再决定换件或改系统配置。
5. **日志缺失不是否定证据**：有限日志中的缺失只能限定结论边界；需要补采样或受控复现。
6. **测量前提**：明确稳态、单位、样本量、定位/健康状态等前置条件；违反条件的运行作废；正负实验结果都要记录。
7. **不把派生值当物理事实**：融合/滤波遥测可能包含内部修正；需要直接测量或受控扰动验证。
8. **稳定身份**：设备用序列号、UID、物理总线/拓扑位置定位，不用 COM 号、枚举顺序或显示名。
9. **配置也是变量**：换单件前先 diff 配置；复现故障时固定配置；跨版本升级做全量参数 diff，分类改名、语义反转、默认值变化、工具写入和人工修改。
10. **刷写后验证**：不断电，校验版本/身份，重查输出路由、协议、配置转换、执行器顺序/方向和端到端链路，保留升级前基线用于回滚。
11. **风险接受**：不要把厂商不建议的维护/校准模式当作捷径；接受残余风险时记录理由、缓解措施和重新开启决策的条件。
12. **台架安全**：拆桨/卸负载；断电接线或插拔天线；首次上电用限流电源；按官方图片核对针序；禁止向非供电口反灌电源。

## 5. 记忆系统协议

### 5.1 分层

| 内容 | 位置 |
|---|---|
| 每轮必须知道的目标、状态、约束、指针 | Runtime Memory |
| 项目入口与当前状态 | 根 `README.md` |
| 操作规范 | 根 `AGENTS.md` |
| 原子事实、决策、实体、关系 | Memory Space：`Firefly Ledger` |

不创建独立的 FACT / DECISION / CURRENT / ARCHITECTURE / OPERATIONS 文档。

### 5.2 账本条目格式

**事实**：

```text
[FACT-<slug>] Claim: <一句话事实>.
Evidence: <路径/命令/提交/链接>.
Observed: <YYYY-MM-DD>.
Scope: <适用范围>.
Revisit if: <什么时候需要复查>.
```

字段建议：

```text
category: fact
source: external | user
importance: 2-5
tags: [fact, firefly, <domain>]
entities: [<entity 1>, <entity 2>]
```

**决策**：

```text
[DEC-<slug>] Decision: <决定内容>.
Reason: <为什么>.
Alternatives: <考虑过的其他方案>.
Consequences: <代价和后果>.
Evidence: <来源>.
Revisit if: <什么时候需要重新评估>.
```

字段建议：

```text
category: decision
source: user | external
importance: 4-5
tags: [decision, firefly, <domain>]
entities: [<entity 1>, <entity 2>]
```

规则：

- 一条只存一个事实或一个决策，使用稳定 key。
- 每条必须有来源和复查条件。
- 不把推断写成事实；不确定就写未知。
- 写入前先 recall 查重；重复或冲突时先报告。
- 事实与决策冲突时，决策不是事实，必须连同前提一起复查。

### 5.3 Memory Delta

触发时机：

- 产生新的长期事实或决策；
- 事故复盘完成；
- 架构、命令或验证方式改变；
- 里程碑完成；
- 上下文即将压缩；
- 会话结束。

格式：

```text
MEMORY DELTA
Checkpoint: <里程碑/决策/事故/提交/会话结束>
Runtime: add / replace / remove ...
Ledger:
- FACT-<slug>: category, importance, content, evidence, source
- DEC-<slug>: category, importance, content, evidence, source
Human decision: [ ] applied [ ] rejected
```

只提议，不自动写入。人工审阅后通过插件手动落库。

### 5.4 权威顺序

1. 用户当前指令。
2. 实时工具输出和仓库事实。
3. 人工批准的长期记忆。
4. Agent 推断（默认不作为事实）。

## 6. HANDOFF BRIEF

每次接手后的第一份输出必须包含：

- Goal
- Non-goals
- Current state
- Next action
- Invariants and constraints
- Key facts（从 ledger 召回）
- Key decisions（从 ledger 召回）
- Hazards
- Open questions
- Sources and evidence
- Unknowns

写不出 HANDOFF BRIEF 时，先补齐信息，不要直接开工。

## 7. 明确禁止

- 不修改 `docs/software/` 子模组。
- 不解析 `docs/hardware/**/*_origin.pdf`。
- 不自行下载或抓取缺失的厂商文档/PDF。
- 不用 `git clean -fdx` / `git clean -fX`。
- 不用 `git add -A` / `git checkout -- .` 清理工作树。
- 不把长期数据放在 `temp/`。
- 不自动写入或修改长期记忆。
- 不用 COM 号或枚举顺序作为设备身份。
- 不关闭安全/健康/解锁门禁。
- 不在未验证的情况下声称“已修复”或“已复现”。
- 不把假设、推断或生成报告写成事实。
