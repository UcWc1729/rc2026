#!/bin/bash
# 键盘控制启动脚本

echo "======================================"
echo "  键盘电机控制"
echo "======================================"
echo ""

cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
source install/setup.bash

echo "启动键盘控制..."
echo ""

ros2 run my_package_py keyboard_control
