from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        LogInfo(
            msg=[
                '========================================\n',
                '警告: 键盘控制节点不能通过launch文件启动！\n',
                '请使用以下命令从终端直接运行：\n',
                '  ros2 run rc_keyboard_control keyboard_control_node\n',
                '或者使用参数：\n',
                '  ros2 run rc_keyboard_control keyboard_control_node \\\n',
                '    --ros-args -p linear_speed:=0.5 -p angular_speed:=0.5\n',
                '========================================\n'
            ]
        ),
        # 注意：这里不启动节点，只是显示提示信息
        # 键盘控制节点需要从终端直接运行以访问stdin
    ])
