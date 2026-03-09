#!/bin/bash
# 键盘控制启动脚本

cd "$(dirname "$0")"

echo ">>> 编译相关包"
colcon build --packages-select rc_keyboard_control rc_serial_driver --symlink-install

echo ">>> source install/setup.bash"
source install/setup.bash

# 检查串口驱动节点是否已运行
echo ">>> 检查串口驱动节点..."
if ros2 node list 2>/dev/null | grep -q "serial_driver_node"; then
    echo ">>> 串口驱动节点已运行"
else
    echo ">>> 启动串口驱动节点（后台运行）..."
    # 尝试使用gnome-terminal（如果有图形界面）
    if command -v gnome-terminal &> /dev/null && [ -n "$DISPLAY" ]; then
        gnome-terminal -- bash -c "cd $(pwd); source install/setup.bash; ros2 launch rc_serial_driver serial_driver.launch.py; exec bash" 2>/dev/null &
    else
        # 无图形界面时在后台运行
        nohup bash -c "cd $(pwd) && source install/setup.bash && ros2 launch rc_serial_driver serial_driver.launch.py" > /tmp/serial_driver.log 2>&1 &
    fi
    sleep 2  # 等待串口驱动启动
    echo ">>> 串口驱动节点已启动"
    echo ">>> 提示: 如需查看串口驱动日志，请运行: tail -f /tmp/serial_driver.log"
fi

echo ""
echo ">>> 启动键盘控制节点（全向轮模式）"
echo ""

# 直接运行节点（全向轮模式，默认启用）
ros2 run rc_keyboard_control keyboard_control_node
