"""YES-NK 调试入口（仿 YES-BD2 main_debug.py），自动启用 ok-script 详细调试日志。"""

from main import main

if __name__ == "__main__":
    raise SystemExit(main(["--debug"]))
