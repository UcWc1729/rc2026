from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'port_name',
            default_value='/dev/ttyUSB0',
            description='Serial port device path (e.g., /dev/ttyUSB0)'
        ),
        DeclareLaunchArgument(
            'baudrate',
            default_value='115200',
            description='Serial port baudrate'
        ),
        DeclareLaunchArgument(
            'cmd_vel_topic',
            default_value='/cmd_vel',
            description='Topic name for velocity commands'
        ),
        DeclareLaunchArgument(
            'max_linear_vel',
            default_value='1.0',
            description='Maximum linear velocity (m/s)'
        ),
        DeclareLaunchArgument(
            'max_angular_vel',
            default_value='1.0',
            description='Maximum angular velocity (rad/s)'
        ),
        DeclareLaunchArgument(
            'timeout',
            default_value='0.1',
            description='Timeout for velocity commands (seconds)'
        ),
        Node(
            package='rc_serial_driver',
            executable='serial_driver_node',
            name='serial_driver_node',
            output='screen',
            parameters=[{
                'port_name': LaunchConfiguration('port_name'),
                'baudrate': LaunchConfiguration('baudrate'),
                'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic'),
                'max_linear_vel': LaunchConfiguration('max_linear_vel'),
                'max_angular_vel': LaunchConfiguration('max_angular_vel'),
                'timeout': LaunchConfiguration('timeout'),
            }]
        ),
    ])
