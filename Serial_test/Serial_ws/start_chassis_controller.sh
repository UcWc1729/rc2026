#!/bin/bash

# 底盘速度控制启动脚本

echo "=========================================="
echo "启动底盘速度控制节点"
echo "=========================================="

# 进入工作空间
cd "$(dirname "$0")"

# Source ROS2环境
source /opt/ros/humble/setup.bash
source install/setup.bash

# 启动节点
ros2 run my_package_py chassis_controller \
    --ros-args \
    -p serial_port:=/dev/ttyUSB0 \
    -p baudrate:=115200 \
    -p cmd_vel_topic:=cmd_vel \
    -p heartbeat_rate:=10.0

echo ""
echo "节点已退出"
