#!/bin/bash

# 持续发送速度命令测试脚本

echo "=========================================="
echo "🔄 持续发送速度命令测试"
echo "=========================================="

# 检查串口设备
if [ ! -e /dev/ttyUSB0 ]; then
    echo "错误: /dev/ttyUSB0 设备不存在"
    echo ""
    echo "可用的串口设备:"
    ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  未找到USB串口设备"
    echo ""
    exit 1
fi

# 检查权限
if [ ! -w /dev/ttyUSB0 ]; then
    echo "⚠ 串口没有写权限，尝试添加权限..."
    sudo chmod 666 /dev/ttyUSB0
    if [ $? -eq 0 ]; then
        echo "✓ 权限添加成功"
    else
        echo "✗ 权限添加失败"
        exit 1
    fi
fi

echo ""
cd "$(dirname "$0")"

echo "提示:"
echo "  - 程序将以 50Hz 频率持续发送速度命令"
echo "  - 默认速度: Vx=0.1 m/s"
echo "  - 按 Ctrl+C 停止（会自动发送零速度停止电机）"
echo ""
echo "按回车键开始..."
read

python3 continuous_send.py

echo ""
echo "=========================================="
