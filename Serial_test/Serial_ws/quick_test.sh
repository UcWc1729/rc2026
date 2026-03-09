#!/bin/bash

# 快速测试脚本 - 发送 Vx=0.1, Vy=0, Wz=0

echo "=========================================="
echo "底盘速度控制快速测试"
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
else
    echo "✓ 串口权限正常"
fi

echo ""
echo "运行测试脚本..."
echo "=========================================="
echo ""

cd "$(dirname "$0")"
python3 test_chassis_speed.py

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
