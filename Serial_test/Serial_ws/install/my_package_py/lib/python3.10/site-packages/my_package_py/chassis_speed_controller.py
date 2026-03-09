#!/usr/bin/env python3
"""
@file chassis_speed_controller.py
@brief 底盘速度控制节点 - 通过串口发送速度控制命令
@version 1.0
@date 2026-01-23
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial
import threading
import time
from .protocol_handler import ProtocolHandler


class ChassisSpeedController(Node):
    """底盘速度控制ROS2节点"""
    
    def __init__(self):
        super().__init__('chassis_speed_controller')
        
        # 声明参数
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('cmd_vel_topic', 'cmd_vel')
        self.declare_parameter('heartbeat_rate', 10.0)  # Hz
        
        # 获取参数
        self.serial_port = self.get_parameter('serial_port').value
        self.baudrate = self.get_parameter('baudrate').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        heartbeat_rate = self.get_parameter('heartbeat_rate').value
        
        # 创建协议处理器
        self.protocol = ProtocolHandler()
        
        # 串口对象
        self.serial_conn = None
        self.is_connected = False
        self.serial_lock = threading.Lock()
        
        # 连接串口
        self.connect_serial()
        
        # 创建订阅者 - 订阅速度命令
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            cmd_vel_topic,
            self.cmd_vel_callback,
            10
        )
        
        # 创建定时器 - 发送心跳包
        self.heartbeat_timer = self.create_timer(
            1.0 / heartbeat_rate,
            self.heartbeat_callback
        )
        
        self.get_logger().info(f'Chassis Speed Controller initialized')
        self.get_logger().info(f'Serial Port: {self.serial_port} @ {self.baudrate} baud')
        self.get_logger().info(f'Subscribing to: {cmd_vel_topic}')
        
        # 发送初始测试命令
        self.send_test_command()
    
    def connect_serial(self) -> bool:
        """连接串口"""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.is_connected = True
            self.get_logger().info(f'✓ Serial port connected: {self.serial_port}')
            return True
        except Exception as e:
            self.is_connected = False
            self.get_logger().error(f'✗ Failed to connect serial port: {e}')
            return False
    
    def send_data(self, data: bytes) -> bool:
        """发送数据到串口"""
        if not self.is_connected:
            self.get_logger().warn('Serial port not connected')
            return False
        
        try:
            with self.serial_lock:
                self.serial_conn.write(data)
                self.serial_conn.flush()
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to send data: {e}')
            return False
    
    def send_chassis_speed(self, vx: float, vy: float, wz: float) -> bool:
        """
        发送底盘速度控制命令
        
        Args:
            vx: X方向速度 (m/s)
            vy: Y方向速度 (m/s)
            wz: 旋转角速度 (rad/s)
        """
        frame = self.protocol.pack_chassis_speed(vx, vy, wz)
        
        # 打印调试信息
        self.get_logger().info(
            f'Sending speed command: vx={vx:.3f}, vy={vy:.3f}, wz={wz:.3f} '
            f'[Frame: {len(frame)} bytes]'
        )
        self.get_logger().debug(f'Frame hex: {frame.hex()}')
        
        return self.send_data(frame)
    
    def send_test_command(self):
        """发送测试命令：Vx=0.1, Vy=0, Wz=0"""
        self.get_logger().info('=' * 60)
        self.get_logger().info('Sending TEST command: Vx=0.1, Vy=0, Wz=0')
        self.get_logger().info('=' * 60)
        
        result = self.send_chassis_speed(0.1, 0.0, 0.0)
        
        if result:
            self.get_logger().info('✓ Test command sent successfully')
        else:
            self.get_logger().error('✗ Failed to send test command')
    
    def cmd_vel_callback(self, msg: Twist):
        """接收速度命令并发送到下位机"""
        vx = msg.linear.x
        vy = msg.linear.y
        wz = msg.angular.z
        
        self.send_chassis_speed(vx, vy, wz)
    
    def heartbeat_callback(self):
        """发送心跳包"""
        if not self.is_connected:
            return
        
        timestamp = int(time.time() * 1000) & 0xFFFFFFFF  # 毫秒时间戳
        frame = self.protocol.pack_heartbeat(timestamp)
        
        try:
            with self.serial_lock:
                self.serial_conn.write(frame)
                self.serial_conn.flush()
        except Exception as e:
            self.get_logger().warn(f'Failed to send heartbeat: {e}')
    
    def destroy_node(self):
        """节点销毁时清理资源"""
        if self.serial_conn and self.serial_conn.is_open:
            # 发送停止命令
            stop_frame = self.protocol.pack_chassis_stop()
            try:
                self.serial_conn.write(stop_frame)
                self.serial_conn.flush()
            except:
                pass
            
            self.serial_conn.close()
            self.get_logger().info('Serial port closed')
        
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = ChassisSpeedController()
        
        # 等待一下，确保测试命令发送完成
        time.sleep(0.5)
        
        # 继续运行节点接收其他命令
        rclpy.spin(node)
        
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
