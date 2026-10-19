import configparser
import sys

from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")


def isLeapYear(year: int) -> bool:
    """判断输入的年份是否是闰年"""
    y = int(year)
    if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
        return True
    return False


def getDate() -> str:
    """获取当前电脑的日期和时间，调用本地系统命令 date /t 和 time /t"""
    import subprocess

    date_str = ""
    time_str = ""

    try:
        try:
            result = subprocess.run(
                ["date", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            date_str = result.stdout.strip()
        except Exception:
            result = subprocess.run(
                ["cmd", "/c", "date", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            date_str = result.stdout.strip()
    except Exception as e:
        date_str = f"获取日期失败: {e}"

    try:
        try:
            result = subprocess.run(
                ["time", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time_str = result.stdout.strip()
        except Exception:
            result = subprocess.run(
                ["cmd", "/c", "time", "/t"],
                capture_output=True,
                text=True,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            time_str = result.stdout.strip()
    except Exception as e:
        time_str = f"获取时间失败: {e}"

    return f"{date_str} {time_str}".strip()


tools = [
    {
        "type": "function",
        "function": {
            "name": "getDate",
            "description": "获取当前电脑的日期和时间。调用本地系统命令 date /t 和 time /t 获取日期和时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "isLeapYear",
            "description": "计算输入的年份是否是闰年",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "要判断的年份",
                    }
                },
                "required": ["year"],
            },
        },
    },
]

cp = configparser.ConfigParser()
with open("config.ini", encoding="utf-8") as f:
    cp.read_string("[llm]\n" + f.read())

base_url = cp.get("llm", "base_url").strip('"')
api_key = cp.get("llm", "api_key").strip('"')
model = cp.get("llm", "model").strip('"')

client = OpenAI(base_url=base_url, api_key=api_key)
messages = []

while True:
    try:
        print("please input your prompt")
        user_input = input()
        messages.append({"role": "user", "content": user_input})
    except (EOFError, KeyboardInterrupt):
        break
    print("--")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=False,
        )

        message = response.choices[0].message

        if message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in message.tool_calls
                    ],
                }
            )

            for tool_call in message.tool_calls:
                if tool_call.function.name == "getDate":
                    result = getDate()
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )
                elif tool_call.function.name == "isLeapYear":
                    try:
                        args = tool_call.function.arguments
                        if isinstance(args, str):
                            args = __import__("json").loads(args)
                        year = args.get("year")
                        result = "是闰年" if isLeapYear(year) else "不是闰年"
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result,
                            }
                        )
                    except Exception as e:
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"计算失败: {e}",
                            }
                        )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )

            reply = ""
            for chunk in response:
                delta = chunk.choices[0].delta
                piece = delta.content if delta else None
                if piece:
                    print(piece, end="", flush=True)
                    reply += piece
            messages.append({"role": "assistant", "content": reply})
            print()
        else:
            reply = message.content if message.content else ""
            print(reply, end="", flush=True)
            messages.append({"role": "assistant", "content": reply})
            print()
    except Exception as e:
        print(f"error: {e}")
