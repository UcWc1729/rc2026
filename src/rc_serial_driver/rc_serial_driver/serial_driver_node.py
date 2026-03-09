#!/usr/bin/env python3
"""
@file serial_driver_node.py
@brief 串口驱动ROS2节点 - 与Serial_test版本完全一致
@version 1.0
@date 2026-01-27
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import serial
import threading
import time
from .protocol_handler import ProtocolHandler


class SerialDriverNode(Node):
    """串口驱动ROS2节点（与Serial_test版本完全一致）"""
    
    def __init__(self):
        super().__init__('serial_driver_node')
        
        # 声明参数
        self.declare_parameter('port_name', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('publish_odom', True)
        self.declare_parameter('odom_topic', '/odom_serial')
        self.declare_parameter('timeout', 0.1)
        
        # 获取参数
        self.serial_port = self.get_parameter('port_name').value
        self.baudrate = self.get_parameter('baudrate').value
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.publish_odom = self.get_parameter('publish_odom').value
        odom_topic = self.get_parameter('odom_topic').value
        self.timeout = self.get_parameter('timeout').value
        
        # 创建协议处理器
        self.protocol = ProtocolHandler()
        
        # 串口对象
        self.serial_conn = None
        self.is_connected = False
        self.serial_lock = threading.Lock()
        
        # 自动检测并连接串口
        self.connect_serial()
        
        # 创建订阅者 - 订阅速度命令（队列深度10，与Serial_test一致）
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            cmd_vel_topic,
            self.cmd_vel_callback,
            10  # 队列深度10，与Serial_test版本一致
        )
        
        # 创建里程计发布者（如果启用）
        if self.publish_odom:
            self.odom_pub = self.create_publisher(Odometry, odom_topic, 10)
        
        # 创建定时器，用于读取反馈（50Hz）
        self.feedback_timer = self.create_timer(
            0.02,  # 20ms = 50Hz
            self.read_feedback_callback
        )
        
        # 创建定时器，用于超时检测
        self.timeout_timer = self.create_timer(
            self.timeout,
            self.timeout_callback
        )
        
        self.last_cmd_time = self.get_clock().now()
        self.rx_buffer = bytearray()
        
        self.get_logger().info('Serial driver node initialized')
        self.get_logger().info(f'Serial Port: {self.serial_port} @ {self.baudrate} baud')
        self.get_logger().info(f'Subscribing to: {cmd_vel_topic}')
    
    def find_available_port(self, preferred_port: str) -> str:
        """查找可用的串口设备"""
        # 如果指定的端口存在且可访问，直接使用
        ports_to_try = [preferred_port]
        if preferred_port == '/dev/ttyUSB0':
            ports_to_try = ['/dev/ttyUSB0', '/dev/ttyUSB1']
        elif preferred_port == '/dev/ttyUSB1':
            ports_to_try = ['/dev/ttyUSB1', '/dev/ttyUSB0']
        
        for port in ports_to_try:
            try:
                # 尝试打开（只读模式，不占用）
                test_ser = serial.Serial(port, self.baudrate, timeout=0.1)
                test_ser.close()
                return port
            except:
                continue
        
        return ""
    
    def connect_serial(self) -> bool:
        """连接串口（与Serial_test版本完全一致）"""
        # 自动检测串口
        actual_port = self.find_available_port(self.serial_port)
        if not actual_port:
            self.get_logger().error(
                f'Failed to find available serial port. Tried: {self.serial_port}, /dev/ttyUSB0, /dev/ttyUSB1'
            )
            return False
        
        try:
            self.serial_conn = serial.Serial(
                port=actual_port,
                baudrate=self.baudrate,
                timeout=0.1,  # 与Serial_test版本一致
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.serial_port = actual_port  # 更新为实际使用的端口
            self.is_connected = True
            self.get_logger().info(f'✓ Serial port connected: {actual_port} @ {self.baudrate} baud')
            return True
        except Exception as e:
            self.is_connected = False
            self.get_logger().error(f'✗ Failed to connect serial port: {e}')
            return False
    
    def send_data(self, data: bytes) -> bool:
        """发送数据到串口（与Serial_test版本完全一致）"""
        if not self.is_connected:
            self.get_logger().warn('Serial port not connected')
            return False
        
        try:
            with self.serial_lock:
                self.serial_conn.write(data)  # 写入数据
                self.serial_conn.flush()      # 立即flush，确保数据发送（与Serial_test一致）
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to send data: {e}')
            return False
    
    def send_chassis_speed(self, vx: float, vy: float, wz: float) -> bool:
        """
        发送底盘速度控制命令（与Serial_test版本完全一致）
        
        Args:
            vx: X方向速度 (m/s)
            vy: Y方向速度 (m/s)
            wz: 旋转角速度 (rad/s)
        """
        frame = self.protocol.pack_chassis_speed(vx, vy, wz)
        
        # 打印发送信息（与Serial_test版本一致，使用info级别）
        self.get_logger().info(
            f'Sending speed command: vx={vx:.3f}, vy={vy:.3f}, wz={wz:.3f} '
            f'[Frame: {len(frame)} bytes]'
        )
        
        return self.send_data(frame)
    
    def cmd_vel_callback(self, msg: Twist):
        """接收速度命令并发送到下位机（与Serial_test版本完全一致）"""
        self.last_cmd_time = self.get_clock().now()
        
        # 直接使用消息值（与Serial_test版本一致，不限制速度）
        vx = msg.linear.x
        vy = msg.linear.y
        wz = msg.angular.z
        
        # 立即发送（只在收到消息时发送，无延迟）
        self.send_chassis_speed(vx, vy, wz)
    
    def timeout_callback(self):
        """超时检测回调"""
        elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9
        if elapsed > self.timeout:
            # 超时：可以选择发送停止指令（如果需要安全停止）
            # 当前不发送，因为只在收到消息时发送
            # 注意：Python logger没有debug_throttle，使用debug即可
            self.get_logger().debug(f'No cmd_vel received for {elapsed:.2f} seconds')
    
    def read_feedback_callback(self):
        """读取反馈数据（50Hz）"""
        if not self.is_connected:
            return
        
        try:
            # 读取串口数据
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.read(self.serial_conn.in_waiting)
                self.rx_buffer.extend(data)
                
                # 尝试解析帧
                while len(self.rx_buffer) >= 9:  # 最小帧长度
                    # 查找帧头
                    try:
                        sof_pos = self.rx_buffer.index(ProtocolHandler.SOF)
                    except ValueError:
                        # 没有找到帧头，清空缓冲区
                        self.rx_buffer.clear()
                        break
                    
                    # 移除帧头之前的数据
                    self.rx_buffer = self.rx_buffer[sof_pos:]
                    
                    # 检查是否有足够的数据
                    if len(self.rx_buffer) < 9:
                        break
                    
                    # 尝试解析帧
                    success, cmd_id, frame_data, seq = self.protocol.parse_frame(bytes(self.rx_buffer))
                    
                    if success:
                        # 解析成功，处理数据
                        self.handle_feedback(cmd_id, frame_data)
                        
                        # 计算帧长度
                        payload_len = 2 + len(frame_data)
                        expected_len = 5 + payload_len + 2
                        
                        # 移除已处理的数据
                        self.rx_buffer = self.rx_buffer[expected_len:]
                    else:
                        # 解析失败，移除帧头，继续查找下一个帧头
                        self.rx_buffer = self.rx_buffer[1:]
                
                # 限制缓冲区大小
                if len(self.rx_buffer) > 512:
                    self.rx_buffer.clear()
                    self.get_logger().warn('RX buffer overflow, cleared')
        
        except Exception as e:
            self.get_logger().error(f'Error reading feedback: {e}')
    
    def handle_feedback(self, cmd_id: int, data: bytes):
        """处理反馈数据"""
        if cmd_id == ProtocolHandler.CMD_CHASSIS_FEEDBACK:
            # 解析底盘反馈数据
            feedback = self.protocol.parse_chassis_feedback(data)
            if feedback and self.publish_odom:
                self.publish_chassis_feedback(feedback)
        elif cmd_id == ProtocolHandler.CMD_CHASSIS_ODOM:
            # 解析里程计数据
            self.get_logger().debug(f'Received odom data, length: {len(data)}')
    
    def publish_chassis_feedback(self, feedback: dict):
        """发布底盘反馈数据为里程计"""
        odom = Odometry()
        odom.header.stamp = self.get_clock().now().to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        
        # 设置速度
        odom.twist.twist.linear.x = feedback['velocity_x']
        odom.twist.twist.linear.y = feedback['velocity_y']
        odom.twist.twist.angular.z = feedback['angular_vel']
        
        self.odom_pub.publish(odom)
    
    def destroy_node(self):
        """节点销毁时清理资源"""
        if self.serial_conn and self.serial_conn.is_open:
            # 发送停止命令
            stop_frame = self.protocol.pack_chassis_stop()
            try:
                with self.serial_lock:
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
        node = SerialDriverNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
