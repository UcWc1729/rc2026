#!/bin/bash
# ROS2电机控制启动脚本

echo "======================================"
echo "  ROS2 串口电机控制系统"
echo "======================================"
echo ""

# 检查串口设备
echo "1. 检查串口设备..."
if ls /dev/ttyUSB* 1> /dev/null 2>&1; then
    echo "   找到USB串口设备:"
    ls -l /dev/ttyUSB*
    SERIAL_PORT="/dev/ttyUSB0"
elif ls /dev/ttyACM* 1> /dev/null 2>&1; then
    echo "   找到ACM串口设备:"
    ls -l /dev/ttyACM*
    SERIAL_PORT="/dev/ttyACM0"
else
    echo "   ⚠️  未找到串口设备"
    echo "   请检查STM32是否已连接"
    exit 1
fi

echo ""
echo "2. 设置串口权限..."
sudo chmod 666 $SERIAL_PORT
echo "   ✓ 权限设置完成"

echo ""
echo "3. 加载ROS2环境..."
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
source install/setup.bash
echo "   ✓ 环境加载完成"

echo ""
echo "4. 启动电机控制节点..."
echo "   串口: $SERIAL_PORT"
echo "   波特率: 115200"
echo ""
echo "======================================"
echo "  使用 Ctrl+C 停止节点"
echo "======================================"
echo ""

ros2 run my_package_py motor_controller --ros-args -p port:=$SERIAL_PORT -p baudrate:=115200
