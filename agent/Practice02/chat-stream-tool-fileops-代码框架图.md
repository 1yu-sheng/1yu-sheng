# chat-stream-tool-fileops.py 代码框架图

> 基于 `F:\LLM\agent\Practice02\chat-stream-tool-fileops.py`（514 行）绘制。
> 程序是一个流式多轮工具调用 Agent：LLM 通过 function calling 调用本地文件操作工具完成任务。

## 1. 主程序流程

```mermaid
flowchart TD
    Start(["程序启动"]) --> Init["读取 config.ini<br/>初始化 OpenAI Client<br/>注册 tools 工具清单"]
    Init --> PromptLoop{"输入循环<br/>while True"}

    PromptLoop -->|EOF / Ctrl+C| Exit(["退出"])
    PromptLoop -->|用户输入 prompt| AppendUser["messages.append<br/>role=user"]

    AppendUser --> RoundLoop{"工具轮次循环<br/>for 1..MAX_TOOL_ROUNDS=8"}
    RoundLoop -->|超过最大轮次| StopRound(["打印提示<br/>结束本轮"])
    RoundLoop --> Stream["流式请求<br/>chat.completions.create<br/>stream=True + tools=tools"]

    Stream --> Accum["遍历 stream chunks<br/>1. 打印 content，累积 reply<br/>2. 按 index 累积 tool_call delta<br/>(id / name / arguments 片段)"]

    Accum --> HasTool{"本轮响应中<br/>是否包含 tool_calls？"}

    HasTool -->|否（最终回复）| SaveFinal["messages.append<br/>role=assistant, content=reply"]
    SaveFinal --> PromptLoop

    HasTool -->|是| SaveAssistant["messages.append<br/>role=assistant<br/>content + tool_calls"]
    SaveAssistant --> ExecLoop["逐个处理 tool_call：<br/>json.loads(arguments)<br/>打印 [tool] 调用日志"]
    ExecLoop --> RunTool["runTool(name, args)<br/>统一分发到具体函数"]
    RunTool --> SaveTool["messages.append<br/>role=tool<br/>tool_call_id + content=结果"]
    SaveTool --> RoundLoop

    style RunTool fill:#f9d77e,stroke:#333
    style HasTool fill:#a8d5ff,stroke:#333
```

## 2. 工具分发（runTool）

```mermaid
flowchart TD
    RunTool["runTool(name, args)<br/>整体 try/except 兜底"] --> Dispatch{"按 name 分发"}

    subgraph SG_base["基础工具"]
        T1["getDate()<br/>本地命令 date /t + time /t<br/>subprocess + CREATE_NO_WINDOW"]
        T2["isLeapYear(year)<br/>纯 Python 计算<br/>能被4整除且不能被100整除<br/>或能被400整除"]
    end

    subgraph SG_dir["目录工具"]
        T3["getWorkingDirectory()<br/>os.getcwd()"]
        T4["listDirectory(path)<br/>os.scandir<br/>区分 [DIR]/[FILE]+大小"]
        T5["createDirectory(path)<br/>os.makedirs<br/>已存在则报错"]
        T6["removeDirectory(path)<br/>shutil.rmtree<br/>支持非空目录"]
    end

    subgraph SG_file["文件工具"]
        T7["getFileType(path)<br/>扩展名 + mimetypes<br/>+ 前8KB判文本/二进制"]
        T8["readFile(path)<br/>纯文本检测后读取<br/>utf-8/gb18030 解码<br/>超8000字符截断"]
        T9["createFile(directory, filename, content)<br/>os.makedirs + 写入<br/>已存在则报错"]
        T10["editFile(path, content)<br/>纯文本检测后<br/>覆盖写入"]
        T11["deleteFile(path)<br/>os.remove"]
    end

    subgraph SG_rename["重命名工具"]
        T12["renamePath(path, new_name)<br/>os.rename<br/>文件/目录通用"]
    end

    Dispatch --> T1
    Dispatch --> T2
    Dispatch --> T3
    Dispatch --> T4
    Dispatch --> T5
    Dispatch --> T6
    Dispatch --> T7
    Dispatch --> T8
    Dispatch --> T9
    Dispatch --> T10
    Dispatch --> T11
    Dispatch --> T12

    T1 --> Result["返回结果字符串<br/>成功信息或 错误: ..."]
    T2 --> Result
    T3 --> Result
    T4 --> Result
    T5 --> Result
    T6 --> Guard
    T7 --> Result
    T8 --> Guard2["含纯文本检测<br/>含 _decode_text"]
    T9 --> Result
    T10 --> Guard3["含纯文本检测"]
    T11 --> Guard4["含 _check_not_root"]
    T12 --> Guard5["含 _check_not_root<br/>+ 名称合法性检查"]

    Guard[" _check_not_root<br/>拒绝操作驱动器根目录"]
    Guard --> Result

    style RunTool fill:#f9d77e,stroke:#333
    style Result fill:#c8e6c9,stroke:#333
```

## 3. 数据流与消息历史

```mermaid
sequenceDiagram
    participant U as 用户
    participant M as messages 历史
    participant L as "LLM (流式)"
    participant R as runTool 分发
    participant FS as 本地文件系统

    U->>M: role=user (输入 prompt)
    loop 最多 MAX_TOOL_ROUNDS=8 轮
        M->>L: messages + tools 清单 (stream=True)
        L-->>U: 流式打印 content
        L-->>M: role=assistant (content + tool_calls)
        loop 每个 tool_call
            M->>R: name + json.loads(arguments)
            R->>FS: os / shutil / subprocess 操作
            FS-->>R: 操作结果
            R-->>M: role=tool (tool_call_id + 结果字符串)
        end
    end
    L-->>M: role=assistant (无 tool_calls，最终回复)
    L-->>U: 流式打印最终回复
```

## 4. 工具清单

| 工具 | 必填参数 | 可选参数 | 实现方式 |
|---|---|---|---|
| getDate | - | - | 本地命令 `date /t`、`time /t`（subprocess） |
| isLeapYear | year | - | 纯 Python 计算 |
| getWorkingDirectory | - | - | `os.getcwd()` |
| listDirectory | path | - | `os.scandir` |
| getFileType | path | - | `os.path` + `mimetypes` + 二进制嗅探 |
| readFile | path | - | `open` + utf-8/gb18030 解码 |
| createFile | directory, filename | content | `os.makedirs` + `open(w)` |
| editFile | path, content | - | `open(w)` 覆盖写入 |
| createDirectory | path | - | `os.makedirs` |
| removeDirectory | path | - | `shutil.rmtree`（支持非空） |
| deleteFile | path | - | `os.remove` |
| renamePath | path, new_name | - | `os.rename`（文件/目录通用） |

## 5. 关键常量与安全约束

| 项 | 说明 |
|---|---|
| `MAX_TOOL_ROUNDS = 8` | 单轮对话最多 8 轮工具调用，防止死循环 |
| `MAX_READ_CHARS = 8000` | readFile 读取文本截断上限，防止撑爆上下文 |
| 纯文本检测 | readFile/editFile 通过文件前 8KB 是否含 `\x00` 判断二进制并拒绝 |
| 编码策略 | 优先 utf-8，回退 gb18030，均失败则报错 |
| `_check_not_root` | removeDirectory / deleteFile / renamePath 拒绝操作驱动器根目录 |
| renamePath 名称检查 | 新名称不得包含路径分隔符、不得与已有路径重名 |
