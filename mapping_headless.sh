#!/bin/bash
# 建图模式 - 无图形界面启动（SSH/无显示器可用，各节点在后台运行）
# 不修改 mapping.sh，此为独立脚本

cd "$(dirname "$0")"
mkdir -p launch_log

echo ">>> colcon build"
colcon build --symlink-install

echo ">>> source install/setup.bash"
source /opt/ros/humble/setup.bash
source install/setup.bash

cmds=(
  # "ros2 launch rm_bringup bringup.launch.py"  # 包不存在，已注释
  "ros2 launch livox_ros_driver2 msg_MID360_launch.py"
  "ros2 launch linefit_ground_segmentation_ros segmentation.launch.py"
  "ros2 launch fast_lio mapping.launch.py"
  "ros2 launch imu_complementary_filter complementary_filter.launch.py"
  "ros2 launch pointcloud_to_laserscan pointcloud_to_laserscan_launch.py"
  "ros2 launch rm_navigation online_async_launch.py"
  "ros2 launch rm_navigation bringup_no_amcl_launch.py"
  "ros2 launch rc_serial_driver serial_driver.launch.py"
)

i=0
for cmd in "${cmds[@]}"; do
  i=$((i + 1))
  logname="launch_log/mapping_$(printf '%02d' $i).log"
  echo "Current CMD : $cmd"
  echo "  -> log: $logname"
  nohup bash -c "cd '$PWD' && source /opt/ros/humble/setup.bash && source install/setup.bash && $cmd" >> "$logname" 2>&1 &
  sleep 1
done

echo ""
echo ">>> 所有节点已在后台启动"
echo ">>> 日志目录: ./launch_log/"
echo ">>> 查看日志: tail -f launch_log/mapping_*.log"
echo ">>> 停止所有: pkill -f 'ros2 launch'"
echo ""
