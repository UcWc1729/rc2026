#!/bin/bash

# 确保ROS2环境已加载
if [ -z "$ROS_DISTRO" ]; then
    source /opt/ros/humble/setup.bash
fi

colcon build --symlink-install

cmds=(  # "ros2 launch rm_bringup bringup.launch.py"  # 包不存在，已注释
	"ros2 launch livox_ros_driver2 msg_MID360_launch.py"
	"ros2 launch rplidar_ros rplidar_a2m7_launch.py"
	"ros2 launch linefit_ground_segmentation_ros segmentation.launch.py" 
	"ros2 launch fast_lio mapping.launch.py"
	"ros2 launch imu_complementary_filter complementary_filter.launch.py"
	"ros2 launch pointcloud_to_laserscan pointcloud_to_laserscan_launch.py"
	"ros2 launch icp_localization_ros2 bringup.launch.py"
	"ros2 launch rm_navigation bringup_launch.py"
	"ros2 launch rc_serial_driver serial_driver.launch.py")

for cmd in "${cmds[@]}";
do
	echo Current CMD : "$cmd"
	# 确保在每个终端中正确设置ROS2环境
	# 注意：必须先source ROS2基础环境，再source工作空间环境
	# 确保PYTHONPATH包含ROS2的site-packages
	gnome-terminal -- bash -c "cd $(pwd);source /opt/ros/humble/setup.bash;source install/setup.bash;export PYTHONPATH=/opt/ros/humble/lib/python3.10/site-packages:\$PYTHONPATH;$cmd;exec bash;"
	sleep 0.2
done
