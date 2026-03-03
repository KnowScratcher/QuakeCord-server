import os
def log(msg):
    pass
    # if not os.path.exists("log.txt"):
    #     with open("log.txt", "w", encoding="utf-8") as f:
    #         f.write("")
    # with open("log.txt", "a", encoding="utf-8") as f:
    #         f.write(f"{msg}\n")

def info(msg):
    print(f"INFO:     {msg}")
    log(f"INFO:     {msg}")

def success(msg):
    print(f"\033[32mSUCCESS:  {msg}\033[0m")
    log(f"SUCCESS:  {msg}")

def warning(msg):
    print(f"\033[33mWARNING:  {msg}\033[0m")
    log(f"WARNING:  {msg}")

def error(msg):
    print(f"\033[31mERROR:    {msg}\033[0m")
    log(f"ERROR:    {msg}")

