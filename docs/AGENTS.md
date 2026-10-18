# docs

飞控文档与硬件文档。

## 1. 目录结构

```text
docs/
|-- AGENTS.md
|-- software/     飞控与协议文档，git submodule，只读
`-- hardware/     硬件厂商资料，本地保存，不纳入 git
```

## 2. software

- 四个只读 git submodule：`ardupilot_wiki`、`qgroundcontrol`、`mavlink-devguide`、`mavlink`。禁止在子模组内修改、提交、切换分支或更新指针。
- `ardupilot_wiki`：ArduPilot 与 Mission Planner 文档源。
- `qgroundcontrol`：QGroundControl 用户指南、开发者指南与源码；稀疏检出 `cmake`、`custom-example`、`deploy`、`docs`、`src`、`test`、`tools`。
- `mavlink-devguide`：MAVLink 开发者指南，含 `en`、`zh`、`ko`。
- `mavlink`：MAVLink 协议定义与生成工具；`pymavlink/` 嵌套子模组未初始化。
- 子模组工作树中的 CRLF dirty 不是内容修改；先用 `git diff --ignore-cr-at-eol` 区分。
- 检索顺序：官方文档 → 协议定义 → 源码实现；引用本地文件前实际打开确认。

## 3. hardware

- 按厂商存放：`docs/hardware/<厂商>/`，可按产品 / 主题分层；目录内容不纳入 git。

PDF 转换产物：

```text
<原文件名>.pdf-<uuid>/
|-- full.md                    正文，主读
|-- images/                    图片
|-- *_content_list.json        内容列表
|-- *_origin.pdf               原始 PDF，只留存不解析
`-- ...                        版面、块、模型 JSON
```

URL 转换产物：

```text
<网页标题>-<uuid>/
|-- full.md                    正文，主读
|-- main.html                  网页文件
|-- content_list.json          内容列表
`-- images/                    图片
```

- 先读 `full.md`；接口、接线、尺寸直接看 `images/`。
- `*_origin.pdf` 不解析，只作留存与人工溯源。
- 结构化 JSON 仅在需要定位时使用，不替代正文阅读。
- 转换产物用 `scripts/localize-images.py` 与 `scripts/clean-markdown.py` 处理。
- 本地缺料时只报告缺口，不自行下载、抓取或解析网页。
- 飞控文档与厂商文档冲突时，以厂商文档为准。
