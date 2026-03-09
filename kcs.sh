#!/bin/bash

# 直接串口键盘控制脚本
# 不经过ROS2，直接通过串口发送协议数据

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

# 检查pyserial
if ! python3 -c "import serial" 2>/dev/null; then
    echo "错误: 未安装 pyserial"
    echo "请运行: pip3 install pyserial"
    exit 1
fi

# 运行直接串口键盘控制程序
python3 "$SCRIPT_DIR/src/rc_keyboard_control/rc_keyboard_control/keyboard_control_direct.py" "$@"
