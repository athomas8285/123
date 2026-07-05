"""V3.3.3-Core 桌面启动器 — 双击运行即可"""
import os
import sys
import time
import socket
import webbrowser
import subprocess
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = 5021
HOST = "127.0.0.1"


def is_already_running() -> bool:
    """Check if dashboard is already running on the port."""
    try:
        s = socket.create_connection((HOST, PORT), timeout=1)
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def run_flask():
    """Start Flask dashboard, stream output to console."""
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    subprocess.run(
        [sys.executable, os.path.join(BASE, "dashboard.py")],
        cwd=BASE,
        env=env,
    )


def main():
    print(f"  V3.3.3-Core 管理后台")
    print(f"  {'─' * 40}")

    if is_already_running():
        print(f"  ✅ 已在运行 → http://{HOST}:{PORT}")
    else:
        print(f"  正在启动...")
        threading.Thread(target=run_flask, daemon=True).start()
        # Wait for Flask to be ready
        for _ in range(30):
            time.sleep(0.5)
            if is_already_running():
                break
        print(f"  ✅ 启动成功 → http://{HOST}:{PORT}")

    url = f"http://{HOST}:{PORT}"
    print(f"  浏览器即将打开...")
    time.sleep(1)
    webbrowser.open(url)
    print()
    print(f"  关闭此窗口即可退出。")
    print(f"  {'─' * 40}")
    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  已退出。")


if __name__ == "__main__":
    main()
