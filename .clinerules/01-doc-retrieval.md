# 官方参考材料检索规则 (项目级)

适用范围: 本仓四个子模组 (`ardupilot_wiki/`, `qgroundcontrol/`, `mavlink-devguide/`, `mavlink/`) 下的所有查证作业. 与全局规则 (语言, 编码, 质量门禁) 互补, 不重复其内容; 目录范围与版本口径见上级目录的 `README.md`.

## 1. 先查文档, 源码只用于验证

顺序固定: 官方文档 -> 协议定义 -> 源码实现. 用户问功能怎么用或为什么会这样, 先给文档结论; 只有当文档没写, 或必须确认实现细节时才下探源码, 并在回答里区分哪句来自文档, 哪句来自源码. 不用记忆中的印象替代本地材料.

## 2. 问题类型对应入口

Mission Planner 的用法与行为查 `ardupilot_wiki/planner/` 与 `ardupilot_wiki/common/`; 机型相关配置查 `ardupilot_wiki/` 下对应机型目录 (`copter/`, `plane/`, `rover/`, `sub/`); QGroundControl 的用法查 `qgroundcontrol/docs/en/qgc-user-guide/`, 实现细节查 `qgroundcontrol/docs/en/qgc-dev-guide/` 并用 `qgroundcontrol/src/` 核对; MAVLink 的消息, 命令与方言查 `mavlink-devguide/en/messages/`, 而字段, 单位与 CRC 等机器事实以 `mavlink/message_definitions/v1.0/` 的 XML 为准.

## 3. 引用本地文件前必须打开确认

凡回答里要引用某份材料, 都要实际打开对应文件确认存在与内容, 不凭文件名或目录名推断. 文档里的交叉引用若指向本地路径, 该路径必须真实存在; 遇到指向 `planner2/`, `src/` 之类目录的引用, 直接在本地打开核对, 不需要联网.

## 4. 默认排除噪声路径

除非问题明确指向实现, 检索时排除 `images/`, `assets/`, `logos/`, `frontend/`, `.github/`, `test/`, `translations/`, `resources/` 以及翻译目录中的 `ko/`; 中文问题优先 `zh/`, 英文问题优先 `en/`. 排除只针对检索, 不代表这些内容不存在.

## 5. 版本口径以本地钉住的提交为准

回答涉及版本时以 `git submodule status` 的提交为准, 不引用上游当前状态; 四个子模组均为完整克隆, 需要追溯某段文档何时改动时用子模组内的 `git log`. 发现缺料按 `README.md` 的范围补齐, 不用外部网络内容替代本地参考.

## 6. 调整范围时保持文档一致

新增或调整子模组范围时, 同步更新 `README.md` 的结构表与新机取回步骤. 稀疏范围无法提交入库, 只能靠文档与命令固化, 因此文档与实际必须一致.
