# MedImage Agent Apple 风格前端重构完整计划方案

## 文档元信息

- **文档状态**：Ready for Implementation
- **任务模式**：Architecture and Refactor Mode（以前端架构与视觉系统重构为主）
- **目标仓库**：`xlongwu/MedImage_Agent_WebUI_App`
- **核心修改范围**：`src/frontend/`、相关前端测试、必要的前端设计说明文档
- **默认不修改范围**：后端 API、Pipeline Runtime、审批与安全策略、科学计算实现、Electron 原生窗口配置
- **版本策略**：本任务不顺带修改版本号；建议在独立分支实施，待当前发布冻结结束或获得明确批准后再合并
- **参考设计文件**：
  - `medimage-agent-dashb.png`：项目总览与 AI Assistant
  - `medimage-agent-imagi.png`：医学影像工作区与 QC 指标
  - `medimage-agent-proje.png`：项目管理与项目创建
  - `medimage-agent-tasks.png`：任务执行、审批门禁与产物浏览

---

## 1. 项目目标

本次改造不是简单地把颜色改成灰白色，也不是机械复制 macOS 界面，而是在保留 MedImage Agent 现有业务能力、工作流语义和安全边界的前提下，建立一套统一的 **Apple-inspired 桌面应用设计系统**，并将四个核心页面重构为清晰、轻量、克制、具有层级感的多窗格工作区。

最终需要达到以下结果：

1. 建立统一的颜色、字体、间距、圆角、阴影、材质、动效和交互状态规范。
2. 将当前页面从“通用企业后台卡片堆叠”调整为“桌面生产力工具”的信息架构。
3. 形成稳定的全局导航栏、上下文侧边栏、主工作区和检查器/辅助面板四层结构。
4. 完成项目管理、项目总览、医学影像、任务与审批四个核心页面的 Apple 风格改造。
5. 保留现有 React 状态、Controller、Hook、HTTP API 和后端业务语义，不将纯视觉重构扩散为后端重写。
6. 所有状态、指标、进度、审批结果和产物必须来源于真实数据；参考图中的示例数字不得硬编码进入生产页面。
7. 同时支持浅色、深色、中文、英文和常见桌面宽度。

---

## 2. 当前项目基线判断

### 2.1 技术与架构基线

当前前端采用 React、TypeScript 和 Vite，页面由 `App.tsx` 负责应用级编排，`AppShellView.tsx` 负责工作区组合，各业务页面位于 `features/`，后端请求集中在 `lib/api/`。该结构具备进行渐进式 UI 重构的基础，不需要推翻现有前端数据流。

当前项目已经具备以下可复用基础：

- 系统字体栈、浅色与深色 Token；
- Button、Card、Badge、SegmentedControl、Dialog、Tooltip、IconButton、EmptyState 等 UI 原语；
- AppShell、ProjectShell、TopBar、LifecycleRail 等布局组件；
- 项目、任务、影像、QC、结果、AI Assistant 等已有功能模块；
- 键盘导航、焦点样式、减少动效模式和部分无障碍语义；
- 项目状态、任务状态、影像预览、审批与产物的数据链路。

### 2.2 当前主要问题

1. **视觉语言不完全统一**  
   Token 已经部分接近 Apple 风格，但页面仍同时存在深色顶栏、传统后台卡片、旧式全局 CSS 和不同组件自定义样式，导致整体观感不一致。

2. **应用外壳与参考图的信息架构不一致**  
   当前 AppShell 主要是顶部栏、横向生命周期栏、主区域和浮动检查器；参考图需要更明确的全局竖向导航、上下文侧栏、主工作区和右侧辅助面板。

3. **项目页形态偏卡片画廊**  
   当前 `ProjectsPage` 采用卡片网格，而参考设计更接近 Finder/Settings 风格的分组列表，适合项目数量增加后的快速浏览和筛选。

4. **项目总览信息不够集中**  
   当前 Overview 主要展示下一步建议、若干指标和近期活动，尚未形成“项目状态—工作流进度—数据概览—运行状态—DAG—AI Assistant”的完整桌面工作台。

5. **影像工作区的控制、画布和 QC 未形成稳定三栏**  
   当前 `MedicalImageViewer` 将选择器、切面按钮、画布和状态集中在单一卡片中；参考设计需要左侧控制面板、中央影像画布、右侧 QC 指标面板。

6. **任务页偏表格与详情卡组合**  
   当前 `RunsWorkspace` 更适合历史运行审计，参考图则强调任务列表、当前运行、审批门禁、日志和产物的实时工作区。两者应整合，而不是删除已有审计能力。

7. **参考图包含当前数据契约未必支持的内容**  
   例如 FD 折线图、SNR、tSNR、运动参数、Pause、Stop 等，不得仅为匹配截图而制造假数据或无效按钮。必须先确认现有 API 和类型是否提供真实数据。

---

## 3. 核心约束与非目标

### 3.1 必须保持的架构与安全边界

- `App.tsx` 继续作为应用壳层和编排边界，不在其中堆积新的业务逻辑。
- 前端只通过现有 HTTP API 和批准的 Electron Bridge 与后端交互。
- 前端不得直接访问文件系统。
- 后端审批门禁始终具有最终决定权，前端只负责展示和提交已有审批动作。
- 不允许通过 UI 重构绕过 Approval Gate、执行票据、路径安全、审计和 rawdata 只读约束。
- 不得把 `metadata_only`、`preview`、`partial`、`blocked` 等状态展示为 `computed`、`completed` 或 `validated`。
- AI Assistant 仍然是规划、解释和建议工具，不得在界面上暗示其拥有不受约束的直接执行能力。

### 3.2 本任务非目标

- 不修改科学计算公式或算法实现。
- 不新增 DICOM、NIfTI、QC 或预处理执行路径。
- 不改变后端公共 API 契约，除非拆分为独立、明确批准的数据能力任务。
- 不引入新的状态管理框架。
- 不重做 Electron 主进程、窗口边框或安装打包机制。
- 不为了“像 macOS”而捆绑或分发 Apple 专有字体、图标或受限制资源。
- 不将所有历史技术面板一次性重写；优先改造四个高频核心工作区。
- 不保留长期并行的新旧两套完整 UI。

---

## 4. Apple 风格设计系统定义

## 4.1 设计原则

1. **内容优先**：背景和装饰弱化，项目、影像、状态和审批信息成为视觉主体。
2. **层级清晰**：通过材质、间距、字重和分隔线建立层级，不依赖大量描边和高饱和色块。
3. **克制的深度**：只有浮层、弹窗、Sheet 和重要卡片使用明显阴影；普通列表依靠分隔线组织。
4. **一致的交互模型**：同类动作在所有页面使用相同按钮、菜单、选中、禁用和危险态。
5. **桌面生产力导向**：使用多窗格、工具栏、侧边栏、检查器和状态栏，而不是移动端大卡片堆叠。
6. **状态可信**：颜色只辅助表达，文字和图标必须共同说明状态。
7. **精细但不过度动画**：动效只用于状态变化、面板展开和页面切换，不使用炫技动画。
8. **科学内容高可读**：影像画布、日志、指标、参数和表格区域优先保证对比度与精确性。

## 4.2 色彩 Token

建议在现有 `styles/tokens.css` 上演进，不再建立另一套并行 Token。

### 浅色模式

| 语义 | 建议值 | 使用位置 |
|---|---:|---|
| App Background | `#F5F5F7` | 整体窗口背景 |
| Window Background | `#FBFBFD` | 主工作区底色 |
| Sidebar Material | `rgba(242, 242, 247, 0.82)` | 导航栏、项目栏、控制栏 |
| Toolbar Material | `rgba(255, 255, 255, 0.74)` | 顶部工具栏、悬浮工具条 |
| Primary Surface | `#FFFFFF` | 主要内容面板 |
| Secondary Surface | `#F2F2F7` | 分组背景、输入控件 |
| Separator | `rgba(60, 60, 67, 0.16)` | 普通分隔线 |
| Strong Separator | `rgba(60, 60, 67, 0.26)` | 窗格边界 |
| Primary Text | `#1D1D1F` | 标题与正文 |
| Secondary Text | `#6E6E73` | 说明与次级信息 |
| Tertiary Text | `#8E8E93` | 时间、占位、不可用信息 |
| Accent | `#007AFF` | 主要按钮、选中、链接 |
| Success | `#34C759` | 成功和已完成 |
| Warning | `#FF9F0A` | 警告、待确认 |
| Danger | `#FF3B30` | 失败、停止、删除 |
| Information | `#32ADE6` | 运行中、信息提示 |

### 深色模式

| 语义 | 建议值 |
|---|---:|
| App Background | `#000000` 或 `#101114` |
| Window Background | `#1C1C1E` |
| Sidebar Material | `rgba(28, 28, 30, 0.86)` |
| Primary Surface | `#1C1C1E` |
| Secondary Surface | `#2C2C2E` |
| Separator | `rgba(84, 84, 88, 0.65)` |
| Primary Text | `#F5F5F7` |
| Secondary Text | `#AEAEB2` |
| Accent | `#0A84FF` |

### 色彩使用规则

- 大面积区域不得使用高饱和蓝色背景。
- 状态卡片使用浅色 Tint，而不是实色块。
- 危险色只用于明确的失败、停止、删除、拒绝动作。
- 运行状态必须同时提供文本或图标，不得只依赖红绿颜色。
- 医学影像画布保持接近纯黑或深灰，避免半透明材质影响图像判断。

## 4.3 字体与排版

不捆绑 SF Pro 字体文件，继续使用系统字体栈：

```css
-apple-system,
BlinkMacSystemFont,
"Segoe UI Variable",
"Segoe UI",
"Microsoft YaHei UI",
sans-serif
```

建议排版层级：

| 层级 | 字号 | 字重 | 用途 |
|---|---:|---:|---|
| Display | 32–34px | 700 | 项目库或空状态主标题 |
| Page Title | 26–28px | 650–700 | 页面标题 |
| Section Title | 17–20px | 600 | 面板标题 |
| Body | 14–15px | 400 | 正文和表单 |
| Secondary | 13px | 400–500 | 状态、辅助信息 |
| Caption | 11–12px | 400–500 | 时间、路径、单位、标签 |
| Numeric | 14–32px | 500–700 | 指标、进度、统计值 |

规则：

- 减少全大写标题；仅非常短的分组标签允许使用大写。
- 主标题避免过重字重，正文不使用 600 以上字重。
- 路径、日志、ID、时间戳和数值采用现有等宽字体 Token。
- 中英文布局均不得因字宽变化导致按钮截断或面板溢出。

## 4.4 间距、圆角和阴影

使用 4px 基础单位，常用间距为：`4 / 8 / 12 / 16 / 20 / 24 / 32`。

| 元素 | 建议圆角 |
|---|---:|
| 小型图标容器 | 6–8px |
| 输入框与普通按钮 | 9–10px |
| 卡片 | 14px |
| 大面板 | 16–18px |
| Sheet、Dialog | 20–22px |
| Badge、状态胶囊 | 999px |

阴影规则：

- 普通列表和侧边栏尽量只使用分隔线。
- Card 使用极弱阴影，禁止每个小组件都悬浮。
- Popover、Sheet、Dialog 使用明显但柔和的多层阴影。
- 深色模式降低边框亮度并加强背景层级，不直接复用浅色阴影。

## 4.5 材质和模糊

可在顶部工具栏、侧栏和浮层使用：

```css
background: rgba(...);
backdrop-filter: saturate(180%) blur(18px);
-webkit-backdrop-filter: saturate(180%) blur(18px);
```

必须提供不支持 `backdrop-filter` 时的实色回退。影像画布、日志、表格和核心审批内容不得因透明背景降低可读性。

## 4.6 图标规范

- 优先复用现有 `Icon` 组件和图标映射。
- 使用 16、18、20px 三档尺寸，线宽保持一致。
- 选中态通过背景和前景色变化表达，不切换为完全不同的图标风格。
- 不使用 Emoji 充当正式功能图标。
- 未经批准不新增大型图标依赖；如必须引入依赖，需要同步修改 manifest、lockfile、测试和打包验证。

## 4.7 动效规范

- Hover：120ms。
- 面板切换、展开和选中：180ms。
- Sheet、Dialog：220–260ms。
- 使用现有 easing Token，避免弹跳过强。
- 支持 `prefers-reduced-motion`，减少动效模式下不得保留关键位移动画。
- 进度更新不应造成页面整体跳动。

---

## 5. 整体信息架构与应用外壳

## 5.1 目标布局

建议将应用外壳重构为以下插槽结构：

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Top Toolbar / Project Context / Global Actions                       │
├──────┬────────────────┬──────────────────────────────┬───────────────┤
│      │                │                              │               │
│ Nav  │ Context        │ Main Workspace               │ Inspector /   │
│ Rail │ Sidebar        │                              │ Assistant /   │
│      │                │                              │ Artifacts     │
│      │                │                              │               │
├──────┴────────────────┴──────────────────────────────┴───────────────┤
│ Optional Run Activity / Status Bar                                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 插槽职责

- **Global Navigation Rail**：项目、任务、影像/QC、结果、设置等顶层入口。
- **Context Sidebar**：根据页面展示项目列表、影像控制、任务列表或筛选条件。
- **Main Workspace**：当前页面主要内容。
- **Inspector/Assistant/Artifacts Pane**：展示上下文信息、AI Assistant、QC 指标或产物。
- **Run Activity Bar**：仅在存在活动任务或用户主动展开时显示。

## 5.2 推荐尺寸

| 区域 | 推荐值 |
|---|---:|
| Top Toolbar | 50–52px |
| Global Rail | 54–58px |
| Context Sidebar | 260–300px |
| Inspector Pane | 300–360px |
| Bottom Activity Bar | 36–44px |
| Main Workspace 最小宽度 | 620–720px |

不要把这些数值散落在组件 CSS 中，应集中为 Shell Token。

## 5.3 响应式策略

| 窗口宽度 | 布局策略 |
|---|---|
| 1024px | 保留全局 Rail；Context Sidebar 可折叠；Inspector 以 Sheet/Overlay 打开；主工作区优先 |
| 1280px | Rail + Sidebar + Main；Inspector 默认覆盖或较窄停靠 |
| 1440px | Rail + Sidebar + Main + Inspector 完整四栏 |
| 1920px | 增大主工作区；侧栏保持稳定宽度，避免随窗口无限拉伸 |

其他要求：

- 不使用页面级水平滚动解决布局问题。
- 表格可在自身容器中横向滚动，但关键操作列需保持可见。
- 影像工作区不受普通内容最大宽度限制，应充分使用屏幕空间。
- 项目管理页和设置页可使用内容最大宽度，避免超宽屏信息过散。

## 5.4 Shell 预设

建议定义纯前端的布局预设，而不是在页面内重复写 Grid：

```ts
type WorkspaceChromePreset =
  | "project-library"
  | "project-dashboard"
  | "image-workspace"
  | "task-workspace"
  | "standard-workspace";
```

`AppShellView` 根据当前 `navigation.location` 选择预设，`AppShell` 只负责渲染插槽。不要把页面业务判断继续堆积到 `AppShell` 中。

---

## 6. 四个核心页面改造方案

## 6.1 项目管理页

### 目标

将当前卡片画廊重构为简洁、可扫描的项目库。视觉参考 Apple Settings、Finder 列表和现代 macOS 管理工具，而非传统 CRM 后台。

### 页面结构

1. 顶部工具栏：
   - 页面标题“Projects”；
   - 搜索框；
   - 筛选分段控件；
   - 排序菜单；
   - “Create New Project”主要按钮。

2. 项目列表：
   - 每个项目使用整行列表项；
   - 左侧为类型/状态图标；
   - 中部为项目名、Study ID、数据路径摘要、Subjects/Runs；
   - 右侧为状态 Badge 和更新时间；
   - Hover 时显示次级操作；
   - 当前项目使用轻量选中背景，不使用重描边。

3. 创建项目：
   - 继续复用 `ProjectCreateSheet` 的真实创建流程；
   - 采用右侧 Sheet 或居中 Dialog；
   - 路径选择必须继续通过批准的 Electron Bridge/API；
   - 表单校验、加载、失败和创建成功状态必须完整。

### 数据映射

- 项目数据：`projectController.projects.data`。
- 选择项目：现有 `onSelectProject`。
- 删除项目：现有确认 Dialog 和 `handleDeleteProject`。
- 创建项目：现有 `createProjectFromDirectoryPath` 和目录选择函数。

### 状态要求

必须覆盖：

- 首次加载 Skeleton；
- 项目为空；
- 搜索无结果；
- API 失败但有缓存数据；
- API 失败且无数据；
- 删除中；
- 创建中；
- 项目处于 needs setup、pipeline configured、running、completed、partial、failed 等真实状态。

### 禁止事项

- 不将参考图中的项目、人数和更新时间写死。
- 不新增未连接后端的“Active/Completed/Error”筛选语义；筛选必须依据当前真实字段建立，或明确标记为前端派生视图。
- 不使用纯颜色区分状态。

---

## 6.2 项目总览 Dashboard

### 目标

把 Overview 改造成项目级“控制台”，让用户无需在多个技术面板之间跳转即可理解：当前数据是什么、工作流走到哪里、下一步做什么、正在运行什么、需要审批什么。

### 页面结构

#### A. 左侧项目上下文栏

- 搜索项目；
- 展示项目列表和当前状态；
- 提供“New Project”；
- 项目切换沿用现有项目 Controller；
- 支持折叠，1024px 下默认收起。

#### B. 项目头部

- 项目名；
- Study ID；
- 数据根目录的安全摘要；
- 当前状态 Badge；
- “Configure”进入 Settings/Plan；
- “Resume/Review Run”进入 Runs 或 Preprocessing；
- 不提供绕过审批的直接执行快捷键。

#### C. Workflow Progress

- 复用 `buildLifecycleItems` 的真实状态；
- 展示 Data Import、AI Planning、Approval、Execution、Results 等阶段；
- 阻塞阶段显示原因 Tooltip；
- 完成、运行、等待、阻塞和失败状态视觉一致；
- 阶段点击只负责导航，不直接触发执行。

#### D. 核心信息卡

建议保留三张主要卡片：

1. Dataset Overview：Subjects、Sequences、Files、Storage。
2. AI Model Status：模型、版本、加载状态、上下文等已有真实信息。
3. Latest Run：任务名称、进度、ETA/持续时间、状态。

卡片数量保持克制。没有真实数据时显示 `Unavailable` 或空状态，不用 `0` 冒充真实结果。

#### E. Pipeline DAG

- 优先展示已审核计划或真实运行节点；
- 使用状态颜色和节点图标表达 done/running/pending/blocked/failed；
- 节点点击更新 `selectedPlanNode`，供 Context Inspector 或 Assistant 使用；
- 不显示系统未实际注册或未进入计划的节点；
- 没有计划时显示“Review plan to generate workflow visualization”。

#### F. AI Assistant

- 宽屏时停靠在右侧；
- 中等宽度使用 Sheet；
- 保留 Ctrl/Cmd + J 快捷键；
- 顶部明确显示当前项目和选中上下文；
- 助手建议中的执行动作必须转化为现有审核流程，不允许直接调用未审批执行。

### 数据映射

- 项目信息：`project.data`、`ProjectInventory`。
- 项目列表：`projectController.projects.data`。
- 数据概览：`useDatasetSummary`。
- 模型状态：`useModelStatus`。
- 运行状态：`taskController.tasks` 和 `selectedTask`。
- 工作流状态：`buildLifecycleItems`。
- Assistant：现有 assistant props、消息和 submit handler。

### 页面状态

- 未选择项目；
- 项目加载中；
- 数据为空；
- raw DICOM；
- converted BIDS；
- plan 未审核；
- 等待审批；
- 运行中；
- 部分成功；
- 失败；
- 结果可用。

---

## 6.3 医学影像工作区

### 目标

将现有 Viewer 重构为稳定的三栏影像工作区，并保留科学内容的高对比度和准确状态表达。

### 页面结构

#### A. 左侧控制栏

1. Subject 选择；
2. Sequence/Run 选择；
3. Orientation 分段控件：Axial、Sagittal、Coronal；
4. Display：Brightness、Contrast；
5. Overlays：Activation Map、ROI Atlas 等；
6. 可折叠的 Artifact/Source 信息。

### 控制语义

- Subject、Sequence、Plane、Slice 使用现有影像 Controller。
- Brightness 和 Contrast 可作为纯显示层本地状态，通过 CSS/Canvas 显示处理实现，不写入原始文件。
- Overlay 只有在真实 artifact 和可用 preview 存在时才可启用。
- 没有对应产物时，Toggle 应禁用并说明原因，不能显示伪造热图。

#### B. 中央影像画布

- 使用深色无干扰背景；
- 顶部仅保留缩放、适配、全屏、截图/复制等已实际可用动作；
- 中央显示真实 `preview_url`；
- 保留方向标识、切片索引、尺寸、Spacing、TR 等真实元数据；
- 底部使用 Slice Slider；
- 继续支持方向键、PageUp/PageDown、Home/End 等键盘导航；
- Loading Overlay 不遮挡已有图像信息。

#### C. 右侧 QC 面板

右侧面板分为两类信息：

1. **当前已有真实信息**：
   - validation status；
   - source、subject、sequence 计数；
   - validation issues；
   - 文件维度、体素间距和 warnings；
   - 已有 QC evidence 和 artifact 链接。

2. **需要额外数据契约的高级指标**：
   - Framewise Displacement 曲线；
   - SNR、tSNR；
   - 平移和旋转参数；
   - Outlier volumes。

高级指标只有在现有 API 已返回真实数据时才展示。若当前契约不支持，核心 UI 重构阶段必须使用明确的“Not available / QC evidence not generated”状态，不允许复制参考图中的 0.24mm、142.7、68.3 等示例值。

### 与 Results/QC 页的关系

建议保留 `results` 路由，但将其中的影像浏览重构为 `Image Workspace` 视图：

- 左栏整合 ArtifactBrowser 与影像选择；
- 中部为 MedicalImageViewer；
- 右栏复用 QC evidence/validation；
- 报告和派生模块继续放在次级 Tab 或折叠区域；
- 不新增一套重复的数据请求和状态模型。

### 空状态

必须区分：

- 无项目；
- raw DICOM 尚未转换；
- converted 数据但无可预览文件；
- preview 加载失败；
- QC 未生成；
- overlay 不可用；
- 部分 subject 失败；
- 真实预览可用。

---

## 6.4 Tasks、Approval 与 Artifacts 工作区

### 目标

将 `RunsWorkspace` 从“运行历史表格 + 详情卡”升级为更适合桌面工具的任务工作区，同时保留历史审计、事件、诊断和日志能力。

### 页面结构

#### A. 左侧任务列表

- 显示任务名称、类型、状态、开始时间和简要进度；
- 支持搜索和状态过滤；
- 当前任务采用轻量选中背景；
- 列表可容纳 Running、Queued、Completed、Partial、Failed、Blocked；
- 历史运行表格可作为“History”次级视图保留，而不是完全删除。

#### B. 中央运行详情

1. 页头：任务名称、状态、标签、Pipeline 摘要；
2. 当前阶段与环形/线性进度；
3. Subjects processed、Elapsed、ETA；
4. Approval Gate；
5. 实时 Execution Log；
6. Events、Diagnostics、Audit 等次级 Tab。

#### C. Approval Gate

- 清晰列出已满足和未满足的条件；
- 审批人输入和确认框继续使用现有字段；
- “Approve & Execute”只有在前端基础条件满足时可点击，但后端仍必须再次验证；
- Reject 必须是明确危险动作并要求原因或确认；
- 等待审批、审批失败、审批过期、后端拒绝等状态必须可见；
- UI 不得通过修改本地状态直接把任务标记为 approved。

#### D. Pause/Stop 处理

参考图包含 Pause 和 Stop，但当前核心改造不能假设这些 API 已存在：

- 如果仓库已有真实 Pause/Stop API，则接入并覆盖失败状态；
- 如果没有，则本阶段不展示可点击的假按钮；
- 可以隐藏，或显示禁用状态并注明“Not supported by current runtime”；
- 新增 Pause/Stop 必须另立后端 Feature Bundle，覆盖 runtime、状态机、审计、恢复和测试。

#### E. 右侧 Artifacts

- 按 NIfTI、QC Reports、Logs、Audit Package 等分组；
- 每个条目显示文件名、大小、状态和类型；
- 点击更新 `selectedArtifact` 和 Context Inspector；
- 不直接拼接不安全的本地路径；
- 预览或打开动作继续通过当前 artifact API/安全桥接；
- 部分产物、缺失产物和失效链接必须显式标记。

### 数据映射

- 任务列表：`taskController.tasks`。
- 当前任务：`selectedTask`、`selectedTaskId`。
- 事件与日志：`taskEvents`、`task.logs`、diagnostics logs。
- 审批：现有 `taskApprovalName` 和 approve handler。
- 审计：现有 audit package handler。
- 产物：现有 diagnostics/artifact entries 和 ArtifactBrowser 数据。

---

## 7. 前端组件与代码组织方案

## 7.1 总体原则

- 优先复用现有 UI 原语，不重新创建同义组件。
- 组件拆分以可复用性、职责和测试边界为依据，不按每个视觉小块拆一个文件。
- 复杂页面只负责组合，数据请求和状态派生继续放在 Hook、Controller 或纯模型函数中。
- CSS 优先使用 CSS Modules 和共享 Token；禁止继续向 `styles.css` 增加 Shell 级样式。
- 新旧 UI 迁移完成后删除失去用途的兼容样式，避免长期双轨。

## 7.2 建议新增或调整的组件

### Shell 与布局

- `AppShell`：支持 rail、contextSidebar、main、inspector、statusBar 插槽。
- `WorkspaceFrame` 或 `SplitWorkspaceLayout`：统一多窗格 Grid、分隔线和响应式折叠。
- `GlobalNavigationRail`：顶层竖向图标导航。
- `PaneHeader`：侧栏和检查器的统一标题栏。
- `WorkspaceToolbar`：页面级工具栏。

### 通用 UI

- `MaterialPanel`：统一半透明面板和实色回退。
- `ListRow`：项目、任务、产物共用的桌面列表行。
- `MetricTile`：克制的数值指标组件。
- `StatusIndicator`：状态点、图标和文字组合。
- `ProgressRing`：运行进度，需支持 aria value。
- `InlineNotice`：错误、警告、阻塞和说明状态。

### 业务组件

- `ProjectSidebar`：项目切换和搜索。
- `WorkflowProgress`：项目阶段进度。
- `PipelineDagPanel`：真实计划节点和运行状态。
- `ImageControlSidebar`：Subject、Sequence、Plane、Display、Overlay。
- `QcInspectorPanel`：影像 validation 与真实 QC evidence。
- `TaskSidebar`：任务列表和过滤。
- `ApprovalGatePanel`：审批条件和操作。
- `ArtifactInspector`：产物分组和选择。

命名可在实现前根据仓库现有约定调整，但不得重复已有同义组件。

## 7.3 AppShellView 的调整策略

`AppShellView` 当前已经承担较多页面组合职责。改造时应：

1. 保持现有 API、Controller、Handler 的注入方式。
2. 新增一个纯函数，根据 location 和屏幕能力返回 `WorkspaceChromePreset`。
3. 将 Rail、Context Sidebar、Inspector 的具体内容拆到独立组件。
4. 不在 `AppShellView` 中新增影像滤镜、QC 计算、任务状态机等业务逻辑。
5. 对 Assistant 增加 `dock` 和 `sheet` 两种展示模式，但复用同一消息状态和 submit handler。
6. 对项目页、Dashboard、Results/Image、Runs 使用不同 Shell 预设；其他工作区暂时使用 `standard-workspace`。

## 7.4 依赖策略

当前核心前端依赖较轻，本次优先保持 **零新增运行时依赖**：

- 继续使用现有 SVG/Icon 系统；
- CSS Grid、CSS Variables、backdrop-filter 和原生表单实现布局；
- 不为简单折线图、进度环或分段控件引入大型 UI/Chart 库；
- 如真实 FD 曲线需要复杂交互图表，再单独评估轻量图表方案并经过依赖审批。

---

## 8. 文件审查与预计修改范围

## 8.1 实施前必须阅读

```text
AGENTS.md
PROJECT_STATE.md
src/frontend/package.json
src/frontend/src/App.tsx
src/frontend/src/features/app/AppShellView.tsx
src/frontend/src/layouts/AppShell/
src/frontend/src/features/dashboard/TopBar.tsx
src/frontend/src/features/navigation/LifecycleRail.tsx
src/frontend/src/features/projects/ProjectsPage.tsx
src/frontend/src/features/projects/ProjectCreateSheet.tsx
src/frontend/src/features/workspaces/OverviewWorkspace.tsx
src/frontend/src/features/app/MedicalImageViewer.tsx
src/frontend/src/features/workspaces/ResultsWorkspace.tsx
src/frontend/src/features/workspaces/QCReportsWorkspace.tsx
src/frontend/src/features/workspaces/RunsWorkspace.tsx
src/frontend/src/features/tools/AssistantSheet.tsx
src/frontend/src/features/tools/ContextInspector.tsx
src/frontend/src/styles/tokens.css
src/frontend/src/styles/globals.css
src/frontend/src/styles/typography.css
src/frontend/src/styles/motion.css
src/frontend/src/styles.css
src/frontend/src/components/ui/
```

同时检查上述组件的 CSS Module、测试、i18n message 和类型文件。

## 8.2 预计需要修改

```text
src/frontend/src/features/app/AppShellView.tsx
src/frontend/src/layouts/AppShell/AppShell.tsx
src/frontend/src/layouts/AppShell/AppShell.module.css
src/frontend/src/features/dashboard/TopBar.tsx
src/frontend/src/features/dashboard/TopBar.module.css
src/frontend/src/features/projects/ProjectsPage.tsx
src/frontend/src/features/projects/ProjectsPage.module.css
src/frontend/src/features/projects/ProjectCreateSheet.*
src/frontend/src/features/workspaces/OverviewWorkspace.tsx
src/frontend/src/features/workspaces/OverviewWorkspace.module.css
src/frontend/src/features/app/MedicalImageViewer.tsx
src/frontend/src/features/app/MedicalImageViewer.module.css
src/frontend/src/features/workspaces/ResultsWorkspace.tsx
src/frontend/src/features/workspaces/ResultsWorkspace.module.css
src/frontend/src/features/workspaces/RunsWorkspace.tsx
src/frontend/src/features/workspaces/RunsWorkspace.module.css
src/frontend/src/features/tools/AssistantSheet.*
src/frontend/src/features/tools/ContextInspector.*
src/frontend/src/features/navigation/*
src/frontend/src/components/ui/*（仅受影响的原语）
src/frontend/src/styles/tokens.css
src/frontend/src/styles/globals.css
src/frontend/src/styles/typography.css
src/frontend/src/styles/motion.css
src/frontend/src/i18n/messages/*
相关前端测试文件
```

## 8.3 可能新增

```text
src/frontend/src/layouts/WorkspaceFrame/
src/frontend/src/features/navigation/GlobalNavigationRail.*
src/frontend/src/features/projects/ProjectSidebar.*
src/frontend/src/features/dashboard/WorkflowProgress.*
src/frontend/src/features/dashboard/PipelineDagPanel.*
src/frontend/src/features/results/ImageControlSidebar.*
src/frontend/src/features/results/QcInspectorPanel.*
src/frontend/src/features/tasks/TaskSidebar.*
src/frontend/src/features/tasks/ApprovalGatePanel.*
src/frontend/src/features/tasks/ArtifactInspector.*
src/frontend/src/lib/workspaceChromeModel.ts
```

新增文件必须以实际复用和职责边界为依据；实施 Agent 在完成仓库审查后可以调整文件名，但要在 Completion Report 中说明。

## 8.4 默认只读或禁止修改

```text
src/backend/
desktop/electron/ 主进程和 BrowserWindow 配置
desktop/packaging/
科学计算 kernel、runner、node registry
Approval Gate 后端实现
Pipeline Runtime
持久化 Schema
```

如果纯前端改造无法完成某一参考图能力，必须停止该能力的实现并报告数据契约缺口，而不是顺手修改受保护模块。

---

## 9. 分阶段实施计划

## 阶段 0：基线审查与差异清单

### 工作内容

1. 阅读仓库规则、当前状态和所有目标文件。
2. 运行当前前端验证，记录基线。
3. 对四张参考图逐页建立“已有能力、纯视觉差异、数据缺口、后端缺口”矩阵。
4. 列出当前 UI 原语和 Icon 能否复用。
5. 检查现有深色模式、中文、英文和 1024/1280/1440/1920px 表现。
6. 检查当前工作树，保留用户未提交修改。

### 交付物

- 一份实现前差异矩阵；
- 最终确认的修改文件清单；
- 需要单独立项的数据/API 缺口清单。

### 退出条件

- 不再存在“为了匹配截图而需要猜测数据来源”的项目。
- 明确当前发布冻结是否允许合并该 UI 重构。

---

## 阶段 1：统一 Design Token 与 UI 原语

### 工作内容

1. 调整浅色和深色 Token。
2. 统一 Button、IconButton、Card、Badge、Input、SegmentedControl、Dialog、Tooltip 等状态。
3. 建立 Material、Separator、Focus Ring、Hover、Pressed、Disabled、Danger 规范。
4. 清理新页面对硬编码颜色的依赖。
5. 保留旧组件兼容，但禁止新增 Legacy shell selector。

### 测试

- UI 原语单测；
- 键盘焦点；
- disabled、danger、loading；
- dark mode；
- reduced motion。

### 退出条件

- 新页面可只依赖 Token 和 UI 原语完成样式。
- 不需要在业务组件中重复定义按钮和输入框外观。

---

## 阶段 2：重构 AppShell 与全局导航

### 工作内容

1. 将 AppShell 扩展为多插槽桌面布局。
2. 新增 Global Navigation Rail。
3. 将 TopBar 改为轻量半透明工具栏；深色模式使用相应材质。
4. 建立 contextSidebar 和 inspector 的响应式停靠/覆盖模式。
5. 保留 RunActivityBar，但默认不抢占主内容。
6. 建立 `WorkspaceChromePreset` 纯模型。
7. 不修改 Electron 原生窗口 frame。

### 测试

- 各 preset 渲染；
- 导航键盘操作；
- Inspector 和 Assistant 打开/关闭；
- 1024/1280/1440/1920 布局；
- 无页面级水平溢出。

### 退出条件

- 四种核心页面可通过同一 Shell 组合。
- App.tsx 未增加业务状态。

---

## 阶段 3：项目管理页改造

### 工作内容

1. 卡片网格改为桌面列表或分组列表。
2. 重做搜索、筛选、排序和状态展示。
3. 重做 ProjectCreateSheet 的视觉层级。
4. 保留删除确认和项目选择行为。
5. 完善 loading、empty、error、stale-data 状态。

### 测试

- 搜索和过滤；
- 选择项目；
- 删除确认；
- 创建 Sheet；
- 中英文；
- 项目名和路径超长截断。

### 退出条件

- 项目数量较多时仍可快速扫描。
- 无硬编码参考项目数据。

---

## 阶段 4：项目 Dashboard 改造

### 工作内容

1. 加入 ProjectSidebar。
2. 重构项目头部和主要动作。
3. 将 Lifecycle 状态转为 Workflow Progress。
4. 建立 Dataset、Model、Latest Run 三类信息卡。
5. 建立真实 Pipeline DAG 或明确空状态。
6. 将 Assistant 在宽屏模式下停靠到右侧。
7. 保留 Context Inspector 和选中上下文。

### 测试

- 所有项目数据状态；
- 生命周期 completed/running/pending/blocked/failed；
- DAG 节点点击；
- Assistant 上下文；
- 无项目和加载失败。

### 退出条件

- 用户从单页即可判断当前项目状态和下一步。
- 页面不提供绕过审核的执行入口。

---

## 阶段 5：医学影像工作区改造

### 工作内容

1. 拆分 ImageControlSidebar、Canvas、QcInspectorPanel。
2. 保留真实预览判断，禁止 pseudo viewer。
3. 将亮度、对比度实现为纯显示状态。
4. Overlay 只绑定真实 artifact。
5. 增加 Slice Slider、元数据和可访问键盘操作。
6. QC 面板接入现有 validation/evidence。
7. 高级 QC 指标缺失时展示明确不可用状态。

### 测试

- 无预览、raw DICOM、converted no preview、真实 preview；
- subject/sequence/plane/slice；
- brightness/contrast 不修改源数据；
- overlay disabled 与 available；
- 图片加载失败；
- 键盘导航；
- QC issue 展示。

### 退出条件

- 三栏稳定，中央画布优先使用空间。
- 所有指标都有真实来源或明确 unavailable。

---

## 阶段 6：Tasks、Approval 与 Artifacts 改造

### 工作内容

1. 从 RunsWorkspace 抽取 TaskSidebar。
2. 保留历史表格作为次级 History 视图。
3. 重构 Run Detail 为进度、阶段、审批、日志和诊断结构。
4. 将 Approval Gate 作为中心关键区域。
5. 将 Artifact 列表停靠在右侧。
6. Pause/Stop 只在真实 API 存在时接入。
7. 保留事件流重连、审计包生成和诊断复制。

### 测试

- running、pending、completed、partial、failed、blocked；
- stream connected/disconnected；
- approval name 缺失；
- approve 成功与后端拒绝；
- audit loading/failure/success；
- artifact empty/partial/available；
- 任务搜索和过滤。

### 退出条件

- 审批语义没有被弱化。
- 日志和产物在高频工作流中无需跨页查找。

---

## 阶段 7：响应式、深色、i18n 与无障碍收口

### 工作内容

1. 统一四种验收宽度。
2. 完成浅色、深色和系统主题。
3. 检查中文、英文长度。
4. 检查 Tab 顺序、ARIA、Focus、Tooltip 和键盘导航。
5. 检查对比度和非颜色状态表达。
6. 检查 reduced motion。
7. 检查高缩放比例和 Windows 字体渲染。

### 退出条件

- 核心操作完全可通过键盘完成。
- 200% 缩放下不丢失关键操作。
- 主题切换无明显颜色泄漏或不可读区域。

---

## 阶段 8：测试、构建、桌面 Smoke 与文档

### 工作内容

1. 运行格式、类型、测试和构建。
2. 对变更页面进行手工视觉验收。
3. 在可用环境中运行 Electron renderer/launch smoke。
4. 更新前端设计说明或相关长期文档。
5. 检查 `git status --short`，排除截图、dist、coverage、日志和用户数据。
6. 生成 Completion Report。

### 退出条件

- 所有必需验证通过；
- 未通过项目明确记录原因和影响；
- 不将生产构建成功误称为完整 GUI 工作流验证。

---

## 10. 数据契约与参考图占位信息处理

参考图中的以下内容一律视为视觉占位，不是当前实现事实：

- `128 subjects`、`384 runs`、`2,304 files`；
- `GPT-4o-neuro`、`128K tokens`；
- `78%`、`~12 min`；
- FD、SNR、tSNR、运动参数和异常 volume；
- Pause、Stop；
- 具体 NIfTI 文件名和文件大小；
- 示例 Pipeline 节点和完成状态。

实施时使用以下决策顺序：

```text
现有类型和 API 已提供真实数据
→ 直接接入

现有仓库已有数据但页面未接入
→ 复用现有 lib/api、Hook 或 evidence model

只有元数据或规划信息
→ 标注 metadata_only / planned / preview

当前完全没有数据契约
→ 显示 unavailable 或隐藏该模块
→ 将需求记录为独立 Feature Bundle

不得使用 Mock 值伪装为真实运行结果
```

---

## 11. 测试与验收矩阵

## 11.1 自动化验证命令

前端源代码或配置修改后至少运行：

```bash
npm --prefix src/frontend run format:check
npm --prefix src/frontend run typecheck
npm --prefix src/frontend run test
npm --prefix src/frontend run build
```

如修改共享 UI 原语或 Shell，必须运行完整前端测试；不能只运行单页测试。

## 11.2 页面状态矩阵

每个核心页面至少覆盖：

| 状态 | 必须验证 |
|---|---|
| Loading | Skeleton 或 Progress，不闪烁假数据 |
| Empty | 给出原因和下一步 |
| Disabled | 说明为何不可操作 |
| Success | 数据和状态来源真实 |
| Partial | 明确显示部分完成和缺失范围 |
| Warning | 可理解、可定位、不过度阻断 |
| Failure | 错误、重试和诊断入口 |
| Blocked | 展示审批/环境/能力阻塞原因 |
| Offline/Stale | 保留已有数据并说明无法刷新 |

## 11.3 视觉验收

每个核心页面需在以下组合中检查：

- 1024×768；
- 1280×800；
- 1440×900；
- 1920×1080；
- 浅色；
- 深色；
- 中文；
- 英文；
- Windows 125%/150% 缩放；
- 浏览器 200% 缩放的关键操作可达性。

## 11.4 无障碍验收

- 所有 IconButton 有可访问名称。
- SegmentedControl、Tab、List、Progress、Dialog 使用正确语义。
- 选中态不只依赖颜色。
- Focus 不被隐藏在 Sheet 或固定面板后。
- Dialog/Sheet 打开时焦点进入，关闭时返回触发按钮。
- 状态实时更新使用适当的 `aria-live`，避免频繁打断。
- 进度环提供文字和 `aria-valuenow`。

## 11.5 性能验收

- 避免在每次任务流消息更新时重渲染整套 Shell。
- 大量任务和项目列表继续设置合理渲染上限或虚拟化评估。
- backdrop-filter 只用于有限区域。
- 影像预览和 Overlay 不因布局更新重复请求。
- CSS 动效不触发高频大面积 Layout。

---

## 12. 完整验收标准

只有同时满足以下条件，才可判定本轮改造完成：

1. 四个参考页面的核心信息架构已经落地，而不是仅更换配色。
2. 全局导航、上下文侧栏、主工作区和右侧面板具有统一布局逻辑。
3. 项目页采用适合桌面管理工具的列表化结构。
4. Dashboard 能展示真实项目状态、工作流阶段、核心指标、DAG/空状态和 Assistant。
5. 影像页形成控制—画布—QC 三栏，并保留真实预览和键盘导航。
6. Tasks 页形成任务—运行/审批—产物三栏，并保留历史审计能力。
7. 参考图中的任何示例值均未硬编码为真实数据。
8. 不存在无后端能力支持的可点击 Pause、Stop、Execute 或 Overlay。
9. Approval Gate、执行票据、后端状态和安全路径未被弱化。
10. `App.tsx` 未变成新的业务逻辑单体。
11. 新样式使用 Token 和 CSS Modules，没有继续扩张 Legacy shell CSS。
12. 1024、1280、1440、1920px 均无关键内容被遮挡或页面级水平滚动。
13. 浅色、深色、中文、英文均通过检查。
14. 键盘、焦点、状态语义和 reduced motion 满足要求。
15. format check、typecheck、frontend tests 和 build 通过。
16. 若进行了桌面打包或 GUI smoke，报告明确区分 build、launch、smoke 和完整用户工作流验证。
17. 未提交 dist、coverage、截图缓存、日志、数据库、用户影像或其他生成产物。

---

## 13. 主要风险与应对

| 风险 | 影响 | 应对策略 |
|---|---|---|
| 当前发布处于稳定冻结阶段 | 大范围 UI diff 无法直接合并 | 独立分支实施；冻结结束或明确批准后合并 |
| Shell 改造影响所有工作区 | 回归范围大 | 先建立 characterization tests；使用 preset 渐进迁移 |
| 参考图包含未实现能力 | 容易出现假按钮和假指标 | 建立数据差异矩阵；无契约则 unavailable/隐藏 |
| Legacy CSS 与新 CSS 冲突 | 样式泄漏 | 新 Shell 全部 CSS Modules；最后集中清理 legacy |
| 多栏布局在 1024px 拥挤 | 关键内容不可用 | Sidebar 折叠、Inspector Sheet 化，Main 优先 |
| backdrop-filter 在部分环境性能差 | Electron/Windows 卡顿 | 限制使用区域，提供实色回退 |
| 医学影像区域过度透明 | 影响判断和对比度 | 画布与 QC 核心区域使用实色高对比背景 |
| Assistant 停靠导致主区变窄 | Dashboard 空间不足 | 仅宽屏默认停靠，中等宽度使用 Sheet |
| UI 派生状态与后端状态不一致 | 错误展示执行结果 | 以 API 状态为真源，派生模型写纯函数并测试 |
| 组件拆分过细 | 文件数量和维护成本增加 | 只为复用、状态边界或测试边界拆分 |

---

## 14. Git、分支与提交建议

建议分支：

```text
feat/apple-inspired-webui
```

建议按以下顺序形成可审查提交：

1. `refactor(ui): establish apple-inspired design tokens`
2. `refactor(shell): add desktop multi-pane workspace chrome`
3. `refactor(projects): redesign project library and creation sheet`
4. `refactor(dashboard): build project overview workspace`
5. `refactor(viewer): add split image and qc workspace`
6. `refactor(runs): add task approval and artifact workspace`
7. `test(ui): cover responsive states and workflow semantics`
8. `docs(ui): record apple-inspired frontend architecture`

规则：

- 一个实施 Agent、一个分支或 worktree、一个 coherent diff。
- 不使用 `git add .`。
- 不顺带清理无关文件。
- 不在未明确要求时 commit、push、tag 或发布。
- 每阶段提交前检查 `git status --short`。

---

## 15. Stop Conditions

出现以下任一情况时，实施 Agent 必须停止相关能力的编码并报告，不得自行扩大范围：

1. 参考图要求的数据在现有 API、类型和 artifact 中不存在。
2. 需要修改 Approval Gate、Pipeline Runtime、科学计算、持久化 Schema 或安全路径才能继续。
3. 需要新增运行时依赖，但任务未批准依赖变更。
4. 需要修改 Electron BrowserWindow、frameless window 或原生窗口控制。
5. 现有测试表明页面状态语义与文档存在冲突。
6. 当前工作树存在与目标文件冲突的用户修改。
7. 无法在不制造 Mock 数据的情况下实现某个图表、指标或操作。
8. 当前发布冻结规则不允许合并该范围变更。

报告内容必须包括：当前事实、缺失契约、受影响页面、建议独立任务和最小可行降级方案。

---

## 16. Completion Report 格式

实施完成后必须按以下结构汇报：

```markdown
# Completion Report

## 1. Task
- Task mode:
- Delivery goal:
- Branch/worktree:

## 2. Files Changed
- Modified:
- Created:
- Deleted:
- Restored:

## 3. Behavior Delivered
- Previous behavior:
- New behavior:
- Failure/empty/partial behavior:
- Compatibility impact:

## 4. Design System Changes
- Tokens:
- Shared UI primitives:
- Shell presets:
- Responsive behavior:
- Dark mode/i18n/accessibility:

## 5. Data and Safety Verification
- No hardcoded reference metrics:
- Approval Gate preserved:
- Backend status remains authoritative:
- No direct filesystem access:
- Unsupported actions omitted/disabled:

## 6. Validation
- format:check:
- typecheck:
- frontend tests:
- build:
- manual viewport checks:
- Electron/package smoke, if run:

## 7. Known Gaps
- Missing API/data contracts:
- Unvalidated environments:
- Follow-up tasks:

## 8. Git and Artifact Check
- git status summary:
- excluded generated files:
- user data safety confirmation:
```

---

## 17. 推荐的后续独立任务

本 UI 重构完成后，可根据真实数据能力另行立项：

1. **影像 QC 指标数据契约**：FD、SNR、tSNR、运动参数、异常 volume 的后端 Schema、artifact、API、前端类型和验证。
2. **任务 Pause/Stop 与恢复状态机**：运行时控制、审计、失败恢复、UI 和 E2E。
3. **可交互 Pipeline DAG**：真实节点依赖、节点日志、产物 lineage 和故障定位。
4. **可编辑 Overlay 系统**：真实 activation/atlas artifact、多图层混合、opacity、colormap 和 provenance。
5. **视觉回归基础设施**：为四个核心页面建立稳定截图测试或 Storybook/Playwright 视觉基线；引入依赖前需单独审批。
6. **原生桌面窗口风格**：如确实需要 macOS/Windows 原生标题栏融合，作为独立 Desktop/Packaging 任务处理。

---

## 18. 最终实施原则

本方案的核心不是把页面“画得像 Apple”，而是把 MedImage Agent 改造成一套更接近专业桌面科研工具的界面：结构稳定、层级清晰、交互克制、状态可信、科学内容优先。视觉参考图决定布局方向，但代码、API、真实产物和安全规则决定最终能展示什么、能执行什么。
