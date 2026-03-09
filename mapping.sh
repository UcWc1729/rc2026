#!/bin/bash

# 确保ROS2环境已加载
if [ -z "$ROS_DISTRO" ]; then
  source /opt/ros/humble/setup.bash
fi

colcon build --symlink-install
cmds=(  # "ros2 launch rm_bringup bringup.launch.py"  # 包不存在，已注释
	#"ros2 launch rplidar_ros rplidar_a2m7_launch.py"
	"ros2 launch livox_ros_driver2 msg_MID360_launch.py"
	"ros2 launch linefit_ground_segmentation_ros segmentation.launch.py" 
	"ros2 launch fast_lio mapping.launch.py"
	"ros2 launch imu_complementary_filter complementary_filter.launch.py"
	"ros2 launch pointcloud_to_laserscan pointcloud_to_laserscan_launch.py"
	"ros2 launch rm_navigation online_async_launch.py"
	"ros2 launch rm_navigation bringup_no_amcl_launch.py"
	#"ros2 launch rc_serial_driver serial_driver.launch.py"#
	)

for cmd in "${cmds[@]}"
do
	echo Current CMD : "$cmd"
	gnome-terminal -- bash -c "cd $(pwd);source /opt/ros/humble/setup.bash;source install/setup.bash;$cmd;exec bash;"
	sleep 0.2
done
