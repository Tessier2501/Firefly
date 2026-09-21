# MP / QGC / MAVLink 本地文档落地清单

目标：把 Mission Planner、QGroundControl、MAVLink 三套文档的**原件**完整落到本地磁盘，供离线查阅与工具引用。

四个上游仓库以 git submodule 形式挂在 Firefly 之下（见 §4），Firefly 自身只保存子模组指针与本文件。文档中的所有数字来自 2026-09-21 对上游仓库的实测，基准提交、实测方法与子模组机制的验证记录见附录 A。

## 1. 范围

**在范围内**：三套文档的文档原件（RST / Markdown / 图片 / 站点配置），以及 MAVLink 的协议定义 XML。

**不在范围内**：

| 项目 | 原因 |
|---|---|
| RAG、向量索引、切块、embedding | 本次不需要 |
| MissionPlanner C# 源码、QGroundControl `src/` | 只要文档 |
| 文档站点的 HTML 构建产物 | 站点配置与 Markdown 原件已足够，需要网页版时可随时重构建 |
| ArduPilot 飞控源码与飞控文档（`copter/ plane/ rover/ sub/ dev/`） | 未要求。唯一例外见 §3 |

## 2. 三个文档源（实测数据）

### 2.1 Mission Planner

文档所在仓库**不是** Mission Planner 源码仓库，而是 **ArduPilot wiki**。

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/ArduPilot/ardupilot_wiki.git`（分支 `master`） |
| 文档路径 | `planner/source/` |
| 实测规模 | `planner/` 合计 **34 文件 / 1,960.7 KB** |
| 构成 | 19 个 `.rst`（18 个内容页 + `index.rst`）、12 张图、`conf.py`、`Makefile`、`make.bat` |
| 格式 | reStructuredText + Sphinx |
| 语言 | 仅英文 |

19 个 `.rst` 的完整清单（第 1 个是目录页，其余 18 个是内容页）：

```text
planner/source/index.rst                                   <- 目录页(toctree)

planner/source/docs/live-video.rst
planner/source/docs/mission-planner-advanced-installation.rst
planner/source/docs/mission-planner-building.rst
planner/source/docs/mission-planner-configuration-and-tuning.rst
planner/source/docs/mission-planner-features.rst
planner/source/docs/mission-planner-flight-data.rst
planner/source/docs/mission-planner-flight-plan.rst
planner/source/docs/mission-planner-ground-control-station.rst
planner/source/docs/mission-planner-initial-setup.rst
planner/source/docs/mission-planner-installation.rst
planner/source/docs/mission-planner-language-translations.rst
planner/source/docs/mission-planner-overview.rst
planner/source/docs/mission-planner-simulation.rst
planner/source/docs/mission-planner-telemetry-logs.rst
planner/source/docs/opendroneid.rst
planner/source/docs/other-mission-planner-features.rst
planner/source/docs/swarming.rst
planner/source/docs/using-python-scripts-in-mission-planner.rst
```

三个容易混淆的位置（均已核实）：

| 候选 | 实测结果 | 结论 |
|---|---|---|
| `ArduPilot/MissionPlanner` 仓库 | 仓库内**没有**文档目录，根目录是 C# 源码与资源 | 不是文档源 |
| `ArduPilot/MissionPlanner.wiki` | 仅 1 个 `Home.md`，内容为空，最后更新 2021-07-31 | 废弃占位，不是文档源 |
| `ardupilot_wiki/planner2/source/` | 其 `conf.py` 内写着 `project = 'APM Planner 2'` | 是另一款 GCS（APM Planner 2）的文档，不属于 Mission Planner，本次不收 |

### 2.2 QGroundControl

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/mavlink/qgroundcontrol.git`（分支 `master`） |
| 文档路径 | `docs/` |
| 实测规模 | **1,012 文件 / 24.3 MB** |
| 格式 | Markdown + VuePress（配置在 `docs/.vitepress/`） |

分项（实测）：

| 子目录 | 文件数 | 体积 | 说明 |
|---|---|---|---|
| `docs/en/` | 148 | 0.39 MB | 英文，含 `qgc-user-guide/`（100）+ `qgc-dev-guide/`（45） |
| `docs/zh/` | 162 | 0.47 MB | 中文翻译 |
| `docs/ko/` | 162 | 0.49 MB | 韩文翻译 |
| `docs/tr/` | 162 | 0.48 MB | 土耳其文翻译 |
| `docs/assets/` | 366 | 22.4 MB | 图片资源，四语言共用 |
| 其余 | 12 | — | `docs/index.md`、`docs/crowdin_docs.yml`、`docs/public/` 等 |

独立的旧文档仓库 `mavlink/qgroundcontrol-user-guide` **已不存在**（克隆返回 `Repository not found`）。QGC 文档当前只存在于主仓库。

### 2.3 MAVLink

MAVLink 侧有两件性质不同的东西，建议都收。

**(a) MAVLink 开发者指南（文档本体）**

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/mavlink/mavlink-devguide.git`（分支 `master`） |
| 实测规模 | **362 文件 / 11.63 MB**（`--depth 1` 全量） |
| 格式 | Markdown + VitePress（配置在 `.vitepress/`） |

| 子目录 | 文件数 | 体积 |
|---|---|---|
| `en/` | 98 | 1.90 MB |
| `zh/` | 104 | 3.82 MB |
| `ko/` | 104 | 3.81 MB |
| `assets/` | 25 | 1.64 MB |
| `public/` | 4 | 0.04 MB |
| `.vitepress/` | 5 | 0.02 MB |

`en/` 的子目录结构：`about/ contributing/ file_formats/ getting_started/ guide/ mavgen_c/ mavgen_cpp/ mavgen_python/ messages/ services/`。

`en/messages/` 下 **21 个文件**就是消息参考页，按 dialect 一页一份（实测完整清单）：`all.md`、`ardupilotmega.md`、`ASLUAV.md`、`AVSSUAS.md`、`common.md`、`csAirLink.md`、`cubepilot.md`、`development.md`、`dialects.md`、`icarous.md`、`index.md`、`loweheiser.md`、`marsh.md`、`minimal.md`、`paparazzi.md`、`python_array_test.md`、`standard.md`、`stemstudios.md`、`storm32.md`、`test.md`、`uAvionix.md`。这些页面**已随仓库提供**，本地无需运行生成器。

**(b) MAVLink 协议定义（不是文档，但缺了它消息参考无法自证）**

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/mavlink/mavlink.git`（分支 `master`） |
| 路径与规模 | `message_definitions/v1.0/` = **19 文件 / 1,044.8 KB** |
| 内容 | 实测完整 19 个：`all.xml`、`ardupilotmega.xml`、`ASLUAV.xml`、`AVSSUAS.xml`、`common.xml`、`csAirLink.xml`、`cubepilot.xml`、`development.xml`、`icarous.xml`、`loweheiser.xml`、`marsh.xml`、`minimal.xml`、`paparazzi.xml`、`python_array_test.xml`、`standard.xml`、`stemstudios.xml`、`storm32.xml`、`test.xml`、`uAvionix.xml` |
| 附带的 `doc/` | 7 文件：`mavlink_xml_to_markdown.py`、`Doxyfile`、`mavlink.php`、`mavlink_to_html_table.xsl`、`mavlink.css`、`README.md`、`requirements.txt` —— 这是**生成工具**，不是文档内容 |

注：`pymavlink` 在该仓库中是子模块，取文档与 XML 均不需要它。

## 3. 关键结论：Mission Planner 文档是分散的

MP 的 `index.rst` 及其全部内容页**引用了两处不在 `planner/` 内的内容**：

**1. 34 个 `common-*` 页面**，位于 `common/source/docs/`（该目录共 710 个 `.rst`）。已逐个核实**全部存在**：

```text
common-appendix                     common-loading-firmware
common-mission-planning             common-connect-mission-planner-autopilot
common-mp-tools                     common-glossary
common-accelerometer-calibration    common-compass-calibration-in-mission-planner
common-radio-control-calibration    common-esc-calibration
common-auxiliary-functions          common-rcoutput-mapping
common-rc-transmitter-flight-mode-configuration
common-optional-hardware            common-brushless-escs
common-joystick                     common-polygon_fence
common-ac2_simple_geofence          common-rally-points
common-logs                         common-diagnosing-problems-using-logs
common-downloading-and-analyzing-data-logs-in-mission-planner
common-recording-and-playing-back-missions
common-geotagging-images-with-mission-planner
common-planning-a-mission-with-waypoints-and-events
common-camera-shutter-with-servo    common-herelink
common-siyi-zr10-gimbal             common-slcan-f4
common-slcan-f7h7                   common-imu-notch-filtering
common-MAVLink2-signing             common-donation
common-telemetry-landingpage
```

**2. 42 张图片**，位于仓库根 `images/`（不在 `planner/` 内）。例如 `images/mission_planner_screen_flight_plan.jpg`、`images/MP-*.png`、`images/can-slcan-mp-*.png`、`images/mp_*.jpg`。该数字由扫描 `planner/source/**/*.rst` 里全部 `images/*.{png,jpg,jpeg,gif}` 引用去重得到，并已逐个核实存在。

**因此**：只取 `planner/` 会得到一个 1.9 MB 但交叉引用与配图大面积失效的残缺镜像。要「完整落到本地」，至少要同时取 `planner/` + `common/` + `images/`。

**实测体积（首次落地后实测）**：

| 路径 | 文件数 | 体积 |
|---|---|---|
| `planner/` | 34 | 1.91 MB |
| `common/` | 718 | 4.35 MB |
| `images/` | 2,487 | **574.50 MB** |
| 合计 | 3,264 | **580.91 MB** |

也就是 580.91 MB 里有 **98.9% 是 `images/`**，而 MP 页面实际只引用其中 42 张（占该目录文件数的 1.7%）。是否保留整个 `images/` 见 §8 的取舍。

## 4. 落地方式：git submodule

四个上游仓库以 **git submodule（子模组）** 挂在 Firefly 之下。Firefly 只记录每个文档源的**具体提交号**，文档本体不进 Firefly 的历史；`git submodule status` 一眼可见四份文档各停在哪个版本，上游更新时一条命令就地升级。

| 仓库 | 打包体积 | 需要的部分 | 子模组路径 |
|---|---|---|---|
| `ardupilot_wiki` | ≈ 1.36 GB | 1.91 MB + `common/` 4.35 MB + `images/` 574.50 MB | `vendor/ardupilot_wiki` |
| `qgroundcontrol` | ≈ 551 MB | 24.3 MB | `vendor/qgroundcontrol` |
| `mavlink-devguide` | ≈ 18 MB | 11.63 MB | `vendor/mavlink-devguide` |
| `mavlink` | ≈ 15 MB | 1.02 MB | `vendor/mavlink` |

### 4.1 必须先知道的三条实测限制

本机 git 2.55.0 + Windows 实测：

1. **`git submodule add` 不支持 `--filter` 与 `--single-branch`**（`-h` 的用法串只列 `-b / -f / --name / --reference`，man 页另有 `--depth`）；而即使加上 `--depth`，它仍会下载该提交的**全部文件**。对 1.36 GB 的 wiki 与 551 MB 的 QGC 不可接受。
2. **官方配置里没有 `submodule.<name>.sparseCheckout`**（`git help --config` 全量比对确认），所以稀疏检出的路径**无法**写进 `.gitmodules` 持久化。
3. **`submodule.<name>.shallow = true` 会被自动采纳**：`git clone --recurse-submodules` 与 `git submodule update --init` 两条路径都实测得到 depth 1 的浅克隆。

结论：注册过程绕开第 1 条（见 §4.2），第 2 条的后果由 §5 的刷新步骤补偿。

### 4.2 注册步骤

在 Firefly 仓库根目录执行。`docs-sources.md` 已在第一个提交 `ff9db6c` 入库，注册产生的 `.gitmodules` 与四个 gitlink 会进入**下一个**提交。

```powershell
Set-Location 'C:\Users\35723\Documents\GitHub\Firefly'
$up = 'https://github.com'

# 步骤 1：先手工写好 .gitmodules（每个仓库三项：path / url / shallow）
#         这样即可绕开 git submodule add 的全量克隆
git config -f .gitmodules submodule.vendor/ardupilot_wiki.path vendor/ardupilot_wiki
git config -f .gitmodules submodule.vendor/ardupilot_wiki.url  $up/ArduPilot/ardupilot_wiki.git
git config -f .gitmodules submodule.vendor/ardupilot_wiki.shallow true

git config -f .gitmodules submodule.vendor/qgroundcontrol.path vendor/qgroundcontrol
git config -f .gitmodules submodule.vendor/qgroundcontrol.url  $up/mavlink/qgroundcontrol.git
git config -f .gitmodules submodule.vendor/qgroundcontrol.shallow true

git config -f .gitmodules submodule.vendor/mavlink-devguide.path vendor/mavlink-devguide
git config -f .gitmodules submodule.vendor/mavlink-devguide.url  $up/mavlink/mavlink-devguide.git
git config -f .gitmodules submodule.vendor/mavlink-devguide.shallow true

git config -f .gitmodules submodule.vendor/mavlink.path vendor/mavlink
git config -f .gitmodules submodule.vendor/mavlink.url  $up/mavlink/mavlink.git
git config -f .gitmodules submodule.vendor/mavlink.shallow true

# 步骤 2：以 blobless + 稀疏的方式把内容放进子模组路径
#         顺序不可颠倒：先 --no-checkout 克隆，设好稀疏，最后才 checkout
git clone --filter=blob:none --no-checkout --depth 1 --single-branch --branch master `
  $up/ArduPilot/ardupilot_wiki.git vendor/ardupilot_wiki
git -C vendor/ardupilot_wiki sparse-checkout set planner common images
git -C vendor/ardupilot_wiki checkout

git clone --filter=blob:none --no-checkout --depth 1 --single-branch --branch master `
  $up/mavlink/qgroundcontrol.git vendor/qgroundcontrol
git -C vendor/qgroundcontrol sparse-checkout set docs
git -C vendor/qgroundcontrol checkout

git clone --filter=blob:none --no-checkout --depth 1 --single-branch --branch master `
  $up/mavlink/mavlink-devguide.git vendor/mavlink-devguide
git -C vendor/mavlink-devguide checkout          # 全量即可，本身只有 11.63 MB

git clone --filter=blob:none --no-checkout --depth 1 --single-branch --branch master `
  $up/mavlink/mavlink.git vendor/mavlink
git -C vendor/mavlink sparse-checkout set message_definitions doc
git -C vendor/mavlink checkout

# 步骤 3：把 .gitmodules 与四个 gitlink 登记进索引，并写进 .git/config
git add .gitmodules vendor/ardupilot_wiki vendor/qgroundcontrol vendor/mavlink-devguide vendor/mavlink
git submodule init
git submodule status     # 四行都应以空格开头，形如 " <sha> vendor/xxx (heads/master)"
git commit -m "docs: add vendor submodules (Mission Planner / QGC / MAVLink docs)"
```

三点说明：

- `git add` 子模组路径时会提示 `warning: adding embedded git repository`，这是**预期**的：`.gitmodules` 已存在，gitlink 因此被正确记录，`git submodule status` 可验证。
- 可选执行 `git submodule absorbgitdirs`，把各子模组的 `.git` 迁入母仓库的 `.git/modules/`，使布局回到标准形态。**它必须放在 `git submodule init` 之后**：init 之前子模组尚未登记到 `.git/config`，该命令会静默什么都不做（实测：顺序错时无任何输出且 `.git/modules` 不生成；顺序对时四个子模组各打印一行 `Migrating git directory of ...`）。迁移完成后，子模组目录里的 `.git` 变成指向 `.git/modules/...` 的文件。
- `vendor/` 只是建议位置。`.gitmodules` 的 `path` 一旦提交即固定，之后改名要同时改 `path` 并移动目录，建议一次定好。

补充一条设定：四个上游仓库的默认分支都是 `master`（不是 `main`），所以命令里显式写了 `--branch master`。

## 5. 更新与在新机器上重建

**升级到上游最新**（在 Firefly 根目录）：

```powershell
git submodule update --remote --depth 1   # 四个子模组一起更新到记录分支的最新提交
git submodule status                      # 核对新的提交号
git add vendor ; git commit -m "docs: bump vendor submodules"
```

`--remote` 走的是 `.gitmodules` 里记录的分支（默认取远端 HEAD 分支）；带上 `--depth 1` 以免把历史拉回来。**注意**：`--remote` 只做同步，不会自动重新施加稀疏，若发现工作区变大了，重复本节下面的稀疏命令即可。

**在新机器上克隆 Firefly**：

```powershell
git clone --recurse-submodules <Firefly 的远端地址> Firefly
```

实测行为（两项，务必知道）：

| 行为 | 实测结果 |
|---|---|
| `.gitmodules` 里的 `shallow = true` 是否生效 | **生效**，子模组是 depth 1 的浅克隆 |
| 稀疏检出是否保留 | **不保留**，子模组会全量检出该提交（例如 mavlink-devguide 得到 362 个文件，而非稀疏后的 116 个） |
| 检出的是哪个提交 | **记录的提交**，而不是上游当前 tip（隔离实验：远端 tip 已前进到第二个提交，全新克隆仍精确落在记录的第一个提交上）。这是子模组相对「照文档重新克隆」的关键优势：不会静默拿到比文档更新或更旧的内容 |

因此新机器上克隆之后要**重新施加一次稀疏**（`.gitmodules` 没有存放稀疏路径的地方，见 §4.1 第 2 条）：

```powershell
git -C vendor/ardupilot_wiki sparse-checkout set planner common images
git -C vendor/qgroundcontrol sparse-checkout set docs
git -C vendor/mavlink       sparse-checkout set message_definitions doc
```

实测：该命令把工作区从 362 个文件裁剪到 116 个，母仓库与子模组状态均保持干净。但它**不会缩小已经下载的对象**，磁盘占用只有在注册时就走 §4.2 的 blobless 方式才能省下来；若希望新机器也省流量，就在新机器上重复一遍 §4.2 的注册流程。

**可选的省流量方案：`submodule.<name>.update = none`**

隔离实验（纯本地仓库，与上游无关）确认：

| 行为 | 实测结果 |
|---|---|
| `.gitmodules` 写入 `submodule.<name>.update = none` 后执行 `git clone --recurse-submodules` | 打印 `Skipping submodule '<path>'`，该子模组**完全不克隆**（目录为空、零字节） |
| 此时 `git submodule status` | 该行带 `-` 前缀（未初始化） |
| 改用 `git submodule update --init --checkout <path>` | 命令行 `--checkout` **可以覆盖**该设置，正常克隆并检出记录的提交 |

代价：它会改变日常语义 —— `git submodule update` 与 `update --remote` 默认会跳过这些子模组，必须显式加 `--checkout`。因此**当前 `.gitmodules` 里没有写入该设置**，默认保持标准语义；只有在「新机器上希望像首次注册那样逐仓库 blobless + 稀疏、一字节不多下」时才临时启用，拉完再移除。若决定长期启用，务必把本节的两条更新命令都改成带 `--checkout` 的写法。

## 6. 落地目录

```text
Firefly/                             <- 超级仓库，只存指针与本文件
├── .gitmodules                      # 四个子模组的 path / url / shallow
├── docs-sources.md                  # 本文件
└── vendor/
    ├── ardupilot_wiki/              # 子模组；稀疏 planner/ common/ images/
    │   ├── planner/source/          #   Mission Planner 文档（19 rst + 12 图 + conf.py）
    │   ├── common/source/docs/      #   MP 引用的 34 个 common-* 页面
    │   └── images/                  #   MP 引用的 43 张图
    ├── qgroundcontrol/              # 子模组；稀疏 docs/
    │   └── docs/                    #   en/ zh/ ko/ tr/ assets/ public/ + .vitepress/
    ├── mavlink-devguide/            # 子模组；全量（en/ zh/ ko/ assets/ + .vitepress/）
    └── mavlink/                     # 子模组；稀疏 message_definitions/ doc/
        ├── message_definitions/v1.0/    # 19 个 dialect XML
        └── doc/                         # XML 转 Markdown 的生成工具
```

## 7. 落地后校验清单

**子模组层面**

1. `git submodule status` 输出四行，且每行**以空格开头**（`-` 表示未初始化，`+` 表示工作区提交与记录不一致，两者都不应出现）。
2. 四行的提交号与附录 A 的基准提交一致，或你确认已升级到别的版本。
3. `git status` 干净，不出现 `modified: vendor/...`。
4. 各子模组的 `git sparse-checkout list` 与预期一致：`vendor/ardupilot_wiki` 返回 `planner`、`common`、`images`；`vendor/qgroundcontrol` 返回 `docs`；`vendor/mavlink` 返回 `doc`、`message_definitions`。
5. `git -C vendor/<name> rev-parse --is-shallow-repository` 输出 `true`（确认 `shallow = true` 生效）。

**内容层面**

6. `vendor/ardupilot_wiki/planner/source/` 的 `.rst` 数量 = **19**（18 个内容页 + `index.rst`）；`planner/` 合计 = **34 文件**。
7. `vendor/ardupilot_wiki/common/source/docs/` 中存在 §3 列出的 **34 个** `common-*` 页面。
8. `vendor/ardupilot_wiki/images/` 中存在 §3 引用的 **42 张**图片。
9. `vendor/qgroundcontrol/docs/en/` 文件数 = **148**；若只收英文，`docs/` 合计约为 148 + 366 + 12 = **526 文件**；全语言则为 **1,012 文件**。注意子模组目录本身的总文件数会更多（实测 1,051），因为 cone 模式的稀疏检出**总会带上仓库顶层文件**（`CMakeLists.txt`、`README.md` 等，实测多出 39 个）。
10. `vendor/mavlink-devguide/en/messages/` 文件数 = **21**。
11. `vendor/mavlink/message_definitions/v1.0/` 文件数 = **19**。
12. 抽查编码：抽 5 个 `.rst` 与 5 个 `.md`，确认均为 UTF-8 且无乱码。
13. 抽查交叉引用：在 `planner/source/index.rst` 的 toctree 中任选 2 条 `common-*` 链接，确认目标文件存在。

## 8. 可选档位

**Mission Planner 范围**（作用于 `vendor/ardupilot_wiki` 的稀疏路径；三选一，默认 A 档）：

| 档 | 稀疏路径 | 实测体积 | 结果 |
|---|---|---|---|
| A（当前采用） | `planner common images` | 580.91 MB | 交叉引用与配图完整 |
| B | `planner` + `common` | 6.26 MB | 文字与交叉引用完整，仅缺 42 张配图 |
| C | 不设稀疏 | 整个 wiki tip | 会一并带入飞控文档（`copter/ plane/ rover/ sub/ blimp/` 等），超出本次范围 |

切换方式：`git -C vendor/ardupilot_wiki sparse-checkout set <上表的路径>`。从 A 换到 B 会把约 578 MB 的 `images/` 从工作区剔除，换回 A 会补齐。

⚠️ 缩减稀疏路径**只裁剪工作区，不会缩小已经下载的 `.git` 对象**（实测 `sparse-checkout set` 不触碰 pack）。当前 `.git/modules/vendor/ardupilot_wiki` 内约有 550 MB 的 pack，要真正回收空间需要重新注册该子模组，或对子模组执行 `git gc`（后者本次未实测）。

**语言范围**（默认全收，体积可忽略；需要精简时对相应子模组加稀疏即可）：

| 文档集 | 可选语言 | 体积增量 | 建议 |
|---|---|---|---|
| QGC | `zh/` | +0.47 MB | 收 |
| QGC | `ko/`、`tr/` | 各约 0.48 MB | 视需要，不要时删目录即可 |
| MAVLink | `zh/` | +3.82 MB | 收 |
| MAVLink | `ko/` | +3.81 MB | 视需要 |
| MP | 无翻译版本 | —— | —— |

## 9. 明确不做

- 不建 RAG、向量库或任何检索索引。
- 不把上游文件**本体**提交进 Firefly 的历史；Firefly 只保存四个 gitlink 指针与 `.gitmodules`。
- 不克隆 MissionPlanner C# 源码、QGroundControl `src/`、ArduPilot 飞控源码。
- 不构建文档站点（VuePress / VitePress / Sphinx 的 HTML 产物）。站点配置（`.vitepress/`、`conf.py`）随原件保留，需要离线网页版时再单独构建。
- 不取 `ardupilot_wiki` 的 `frontend/`、`logos/`、`scripts/`，不取 `mavlink` 的 `pymavlink` 子模块。

## 附录 A：基准提交与实测方法

数据采集于 2026-09-21，对应以下提交：

| 仓库 | 提交 | 提交日期 |
|---|---|---|
| `ArduPilot/ardupilot_wiki` | `e550458ed4f4a73ef4030efa766622aba219984a` | 2026-09-20 |
| `mavlink/qgroundcontrol` | `6f1f4368de08fe093291c63ac7f012c797aaf3c4` | 2026-09-20 |
| `mavlink/mavlink-devguide` | `e27e862fb9ec5d185dc84ad5496fbc94a897304f` | 2026-09-20 |
| `mavlink/mavlink` | `3203f89c510337c0088244735c6a5056c52b5a28` | 2026-09-21 |
| `ArduPilot/MissionPlanner.wiki` | `8d0788989386be7b80de43bcee9950d5abcbeea2` | 2021-07-31 |

方法：

1. GitHub REST API 读取仓库元数据与目录切分。
2. `git clone --filter=blob:none --no-checkout --depth 1` 取完整目录树，用 `git ls-tree -r` 统计文件数与扩展名分布。
3. `sparse-checkout set <path>` 加 `checkout` 后，按磁盘上的实际文件统计体积。
4. 交叉引用由扫描 `planner/source/**/*.rst` 中的 `common-*` 与 `images/` 引用得到，再回查目录树核实存在性。

计量口径：仓库打包体积取自 GitHub API 的十进制 KB（1000 进制）；文件树的体积按 1024 进制统计。

原先标注「未实测」的 `common/source/docs/` 与 `images/` 体积，已在首次落地后实测（见 §3 的表格）；至此无遗留未实测项。

### 子模组机制的实测记录

以下每条都在本机 git 2.55.0 + Windows 上实际执行过（隔离实验与真实仓库各若干）：

| 验证项 | 实测结果 |
|---|---|
| `git submodule add --depth 1 --filter=blob:none` | **失败**：`submodule add` 不认识 `--filter` 与 `--single-branch`；只用 `--depth` 仍会把该提交的全部文件下载下来 |
| 手工写 `.gitmodules` + blobless 稀疏克隆 + `git add` 注册 | **成功**：`git submodule status` 得到 ` 3203f89c… vendor/mavlink (heads/master)`，`sparse-checkout list` 返回 `doc` 与 `message_definitions` |
| 在尚无任何提交的仓库里注册 | **成功**（未诞生分支上 `git add` 与 `git submodule init` 均正常） |
| 新克隆是否采纳 `shallow = true` | **是**；`clone --recurse-submodules` 与 `submodule update --init` 两条路径都得到 `is-shallow = true` |
| 新克隆是否保留稀疏 | **否**（得到 362 个文件而非 116 个）；重新执行 `sparse-checkout set` 可裁剪回 116 个 |
| 新克隆落在哪个提交 | **记录的提交**；远端 tip 已前进一个提交，克隆仍精确落在被记录的那个之上 |
| `git submodule absorbgitdirs` 的时机 | **必须在 `submodule init` 之后**：之前调用静默无操作（`.git/modules` 不生成），之后调用四个子模组各打印一行迁移信息 |
| `submodule.<name>.update = none` | 新克隆**整体跳过**该子模组（输出 `Skipping submodule ...`，目录为空、零字节）；`update --init --checkout` 可从命令行覆盖 |
| `git submodule update --remote --depth 1 <path>` | 可用，正常同步且不拉历史 |
| 是否存在 `submodule.<name>.sparseCheckout` 配置 | **不存在**（`git help --config` 全量比对确认） |
| 本地路径作为子模组 URL | git 默认拒绝（`fatal: transport 'file' not allowed`），隔离实验须加 `-c protocol.file.allow=always`；本方案用 https URL，不受影响 |

