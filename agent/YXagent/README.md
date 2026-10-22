# YXAgent

> 分层架构的终端智能体 —— `core` 与 UI 分离，`core` 可被 TUI / Web / Desktop / Mobile 共享。

YXAgent 由 `Practice02/chat-stream-tool-fileops.py` 重构而来。原脚本把"模型调用 / 工具执行 / 终端交互"混在一个文件里；
本项目把同样的能力拆成 **业务内核（core）** 与 **界面层（tui）**，核心目标是：

- 业务逻辑与界面彻底解耦，core 不依赖任何 UI 框架；
- 同一份 core 可以驱动多种前端，后续新增 Web / Desktop 端只需写界面层；
- 保持"流式输出 + 工具调用 + 文件操作"的完整能力，并补上原版缺失的工程化基础（分层、测试、配置、沙箱）。

---

## 目录结构

```
YXagent/
├── core/                     # 业务内核：零 UI 依赖
│   ├── domain/               # 领域层：模型、事件、错误
│   │   ├── models.py         #   Message / ToolCall / ToolSpec ...
│   │   ├── events.py         #   AgentEvent 事件契约
│   │   └── errors.py         #   统一异常体系
│   ├── ports/                # 端口层：抽象接口（依赖倒置）
│   │   ├── llm.py            #   LLMClient
│   │   └── tools.py          #   Tool / ToolRegistry
│   ├── application/          # 应用层：Agent 编排（业务核心）
│   │   └── agent_service.py  #   AgentService：事件流的唯一生产者
│   ├── infrastructure/       # 基础设施层：具体实现
│   │   ├── llm/              #   OpenAI 兼容客户端
│   │   └── tools/            #   内置工具集 + 文件系统服务
│   ├── config.py             # 配置加载（ini / 环境变量）
│   ├── bootstrap.py          # 组合根：create_agent_service()
│   └── __init__.py           # 门面：前端只从这里导入
│
├── tui/                      # 终端前端（Textual）
│   ├── app.py                #   应用外壳、命令行入口
│   ├── presenter.py          #   事件 → 界面动作的翻译层
│   ├── screens/chat_screen.py
│   ├── widgets/              #   消息气泡、工具面板、输入框、状态栏
│   └── styles.tcss
│
├── tests/                    # pytest 测试
├── config.example.ini        # 配置模板
└── pyproject.toml
```

---

## 快速开始

### 1. 安装依赖

```bash
cd YXagent
pip install -e ".[dev]"
```

### 2. 配置

复制配置模板并填入实际值：

```bash
cp config.example.ini config.ini
```

```ini
[llm]
base_url = "http://127.0.0.1:1234/v1"
api_key  = "your-api-key"
model    = "qwen/qwen3-4b-2507"
```

也可以用环境变量覆盖（优先级高于配置文件）：

```bash
export YXAGENT_BASE_URL="http://127.0.0.1:1234/v1"
export YXAGENT_API_KEY="your-api-key"
export YXAGENT_MODEL="qwen/qwen3-4b-2507"
```

> `config.ini` 已加入 `.gitignore`，不会被提交。

### 3. 运行

```bash
python -m tui
# 或安装后
yxagent
```

常用参数：

```bash
python -m tui -c path/to/config.ini   # 指定配置文件
python -m tui -w /path/to/workspace   # 指定工具工作目录
```

### 4. 快捷键

| 快捷键 | 作用 |
| --- | --- |
| `Enter` | 发送 |
| `Shift+Enter` | 输入框内换行 |
| `Ctrl+L` | 清空对话历史 |
| `Ctrl+T` | 查看当前可用工具 |
| `Ctrl+Q` | 退出 |

---

## 架构设计

### 依赖方向

```
        ┌──────────────────────────────────────────┐
        │  前端（可替换）                          │
        │  tui  /  web  /  desktop  /  mobile     │
        └───────────────────┬──────────────────────┘
                            │ 只依赖 core 的公共 API
                            │ 驱动 AgentService.run_turn()
                            │ 消费 AgentEvent 异步事件流
        ┌───────────────────▼──────────────────────┐
        │  core（UI 无关）                          │
        │                                          │
        │  application ──► ports ◄── infrastructure │
        │       │                                  │
        │     domain（模型 / 事件 / 错误）          │
        └──────────────────────────────────────────┘
```

依赖始终指向内部：`application` 依赖 `ports` 抽象，`infrastructure` 实现 `ports`，
`domain` 不依赖任何其他层。前端只从 `core` 门面导入，永远不直接引用 `core.*` 内部子模块。

### 事件流契约

core 与所有前端之间只有一条通道 —— `AgentService.run_turn()` 返回的异步事件流：

| 事件 | 含义 |
| --- | --- |
| `TurnStarted` | 一轮对话开始 |
| `AssistantDelta` | 助手回复的流式文本增量 |
| `AssistantCompleted` | 助手回复结束（含完整文本） |
| `ToolCallStarted` | 一次工具调用开始 |
| `ToolCallFinished` | 一次工具调用结束（含结果与是否成功） |
| `TurnFinished` | 一轮对话结束 |
| `ErrorRaised` | 运行期错误 |

任何前端都可以用同样的代码驱动：

```python
from core import create_agent_service, load_config

service = create_agent_service(load_config("config.ini"))

async for event in service.run_turn("调用 getDate 工具告诉我今天的日期"):
    print(event.type, event)   # TUI 渲染它、Web 推送给浏览器、Desktop 更新界面
```

### 为什么要有一层 presenter

`tui/presenter.py` 把事件翻译成界面动作。它让 `tui/widgets` 与 `tui/screens` 不必理解
core 的内部结构，也保证"换一个前端只需重写表现层"。订阅者可以是同步函数，也可以是协程函数：

```python
presenter.on_assistant_delta(lambda ev: view.append_text(ev.text))

async def on_tool(ev):
    await view.mount(ToolCallView(ev.name, ev.arguments))

presenter.on_tool_started(on_tool)
```

---

## 内置工具

| 工具 | 说明 |
| --- | --- |
| `getDate` | 获取当前电脑的日期和时间 |
| `isLeapYear` | 判断年份是否为闰年 |
| `getWorkingDirectory` | 获取当前工作目录路径 |
| `listDirectory` | 列出目录下的文件与子目录 |
| `getFileType` | 获取文件类型（扩展名 / MIME / 文本或二进制） |
| `readFile` | 读取纯文本文件内容 |
| `createFile` | 创建新文件（可写入初始内容） |
| `editFile` | 用新内容覆盖文件 |
| `createDirectory` | 创建目录 |
| `removeDirectory` | 删除目录及其内容 |
| `deleteFile` | 删除文件 |
| `renamePath` | 重命名文件或目录 |

### 文件沙箱

所有文件工具都被限制在 **工作目录**（默认当前目录，可用 `-w` 指定）之内：

- 解析绝对路径、软链接与 `..` 之后重新校验，越界即拒绝；
- 拒绝操作驱动器根目录（如 `C:\`）；
- 工具不会静默失败，错误会作为 `ToolCallFinished(ok=False)` 回传给模型。

这是相对原版脚本的**安全性增强**：原版允许模型读写任意路径。

---

## 扩展指南

### 新增一个工具

1. 在 `core/infrastructure/tools/` 下实现工具（继承 `FunctionTool` 或直接实现 `Tool` 抽象基类）；
2. 在 `core/infrastructure/tools/builtin.py` 的 `build_default_registry()` 中注册；
3. 所有前端立即可用，无需改动 UI 代码。

```python
class PingTool(FunctionTool):
    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="ping",
            description="测试连通性",
            parameters={"type": "object", "properties": {}, "required": []},
        )

    async def run(self, arguments: dict[str, Any]) -> str:
        return "pong"
```

### 新增一个前端（Web / Desktop）

1. 新建目录（`web/` / `desktop/`），只依赖 `core` 门面；
2. 用 `create_agent_service()` 创建服务；
3. 消费 `AgentService.run_turn()` 的事件流并渲染。

TUI 的 `presenter` 已经演示了这种"事件 → 视图"的映射，Web 端可以把它换成
WebSocket / SSE 推送，Desktop 端可以换成 UI 框架的状态更新。

### 替换大模型供应商

实现 `core.ports.llm.LLMClient` 接口，然后注入：

```python
from core import create_agent_service, load_config

service = create_agent_service(load_config("config.ini"), llm=MyOwnClient())
```

---

## 测试

```bash
cd YXagent
python -m pytest tests -q
```

覆盖范围：

- `test_config.py` —— 配置解析、环境变量覆盖、旧格式兼容；
- `test_agent_service.py` —— 事件流顺序、工具调用循环、会话管理；
- `test_file_tools.py` —— 文件工具读写与沙箱越界拦截；
- `test_tui.py` —— Textual 冒烟测试（启动、消息渲染、工具面板、快捷键）。

TUI 测试使用 Textual 的 `run_test()` 驱动，不需要真实模型。

---

## 与原版脚本的差异

| 项目 | `Practice02/chat-stream-tool-fileops.py` | YXAgent |
| --- | --- | --- |
| 组织方式 | 单文件 | 分层（domain / ports / application / infrastructure） |
| 前端 | 与业务代码耦合 | `core` 与 `tui` 分离，可换前端 |
| 界面 | `input()` / `print()` | Textual 交互式界面，流式渲染 |
| 调用方式 | 同步 `client.chat.completions.create` | 异步 `AsyncOpenAI`，全程 `async` |
| 文件安全 | 可访问任意路径 | 沙箱限制在工作目录内 |
| 测试 | 无 | pytest 单元测试 + TUI 冒烟测试 |
| 配置 | 硬编码常量 | `config.ini` + 环境变量 |
| 可观测性 | 直接打印 | 结构化事件流 |
