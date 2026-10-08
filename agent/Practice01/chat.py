import configparser
import sys

from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

cp = configparser.ConfigParser()
cp.read_string("[llm]\n" + open("config.ini", encoding="utf-8").read())
base_url = cp.get("llm", "base_url").strip('"')
api_key = cp.get("llm", "api_key").strip('"')
model = cp.get("llm", "model").strip('"')

client = OpenAI(base_url=base_url, api_key=api_key)
messages = []

while True:
    try:
        print("please input your prompt")
        messages.append({"role": "user", "content": input()})
    except (EOFError, KeyboardInterrupt):
        break
    print("--")

    try:
        stream = client.chat.completions.create(
            model=model, messages=messages, stream=True
        )
        reply = ""
        for chunk in stream:
            piece = chunk.choices[0].delta.content if chunk.choices else None
            if piece:
                print(piece, end="", flush=True)
                reply += piece
        messages.append({"role": "assistant", "content": reply})
        print()
    except Exception as e:
        print(f"error: {e}")
