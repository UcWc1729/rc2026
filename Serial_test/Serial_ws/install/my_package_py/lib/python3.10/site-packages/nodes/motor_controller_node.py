#!/usr/bin/env python3
"""
@file motor_controller_node.py
@brief 电机控制ROS2节点 - 提供ROS2接口控制电机
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_srvs.srv import Trigger
import serial
import struct
import threading
from typing import Optional, Callable


class SerialBridge:
    """串口通信桥接类"""
    def __init__(self, node: Node, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.node = node
        self.port = port
        self.baudrate = baudrate
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.receive_callback: Optional[Callable] = None
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False
        
        # 协议常量
        self.PROTOCOL_HEADER = 0xAA55
        self.PROTOCOL_FOOTER = 0x0D
        
    def connect(self) -> bool:
        """连接串口设备"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.is_connected = True
            self.node.get_logger().info(f"Successfully connected to {self.port} at {self.baudrate} baud")
            return True
        except Exception as e:
            self.node.get_logger().error(f"Failed to connect to {self.port}: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """断开串口连接"""
        self.running = False
        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=2.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.is_connected = False
        self.node.get_logger().info("Serial connection closed")
    
    def calculate_crc16(self, data: bytes) -> int:
        """CRC16计算 (MODBUS标准)"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc = crc >> 1
        return crc
    
    def build_control_packet(self, motor_type: int, gear: int) -> bytes:
        """构建控制数据包 (7字节)"""
        packet = bytearray()
        packet.extend(struct.pack('<H', self.PROTOCOL_HEADER))
        packet.extend(struct.pack('BB', motor_type, gear))
        crc_data = packet[0:4]
        crc = self.calculate_crc16(crc_data)
        packet.extend(struct.pack('<H', crc))
        packet.extend(struct.pack('B', self.PROTOCOL_FOOTER))
        return bytes(packet)
    
    def send_motor_control(self, motor_type: int, gear: int) -> bool:
        """发送电机控制命令"""
        if not self.is_connected or not self.ser:
            self.node.get_logger().warn("Serial port not connected")
            return False
        
        try:
            packet = self.build_control_packet(motor_type, gear)
            self.ser.write(packet)
            
            motor_name = "3508" if motor_type == 0x01 else "2006"
            gear_names = ["STOP", "LOW", "MID", "HIGH"]
            gear_name = gear_names[gear] if gear < len(gear_names) else "UNKNOWN"
            
            self.node.get_logger().info(f"Sent control: Motor={motor_name}, Gear={gear_name}")
            
            hex_str = ' '.join([f'{b:02X}' for b in packet])
            self.node.get_logger().debug(f"Raw packet: {hex_str}")
            
            return True
            
        except Exception as e:
            self.node.get_logger().error(f"Failed to send motor control: {e}")
            return False
    
    def start_receiving(self, callback: Callable):
        """启动数据接收线程"""
        self.receive_callback = callback
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        self.node.get_logger().info("Started serial receive thread")
    
    def _receive_loop(self):
        """数据接收循环"""
        state = 'header1'
        packet_buffer = bytearray()
        expected_length = 7
        
        while self.running and self.is_connected and self.ser:
            try:
                if self.ser.in_waiting:
                    byte = self.ser.read(1)[0]
                    
                    if state == 'header1':
                        if byte == 0xAA:
                            packet_buffer = bytearray([byte])
                            state = 'header2'
                        else:
                            state = 'header1'
                            
                    elif state == 'header2':
                        if byte == 0x55:
                            packet_buffer.append(byte)
                            state = 'data'
                        else:
                            state = 'header1'
                            
                    elif state == 'data':
                        packet_buffer.append(byte)
                        if len(packet_buffer) >= expected_length:
                            if self.receive_callback:
                                self.receive_callback(packet_buffer)
                            state = 'header1'
                            packet_buffer = bytearray()
                            
            except Exception as e:
                self.node.get_logger().error(f"Error in receive loop: {e}")
                state = 'header1'
                packet_buffer = bytearray()

class MotorControllerNode(Node):
    def __init__(self):
        super().__init__('motor_controller')
        
        # 声明参数
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        
        # 获取参数
        port = self.get_parameter('port').get_parameter_value().string_value
        baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value
        
        # 创建串口桥接实例
        self.serial_bridge = SerialBridge(self, port, baudrate)
        
        # ROS2订阅者
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        # ROS2服务
        self.control_3508_service = self.create_service(
            Trigger,
            '/motor_3508_control',
            self.handle_3508_control
        )
        
        self.control_2006_service = self.create_service(
            Trigger,
            '/motor_2006_control', 
            self.handle_2006_control
        )
        
        # 连接串口
        if not self.serial_bridge.connect():
            self.get_logger().error("Failed to connect to serial port, node will exit")
            return
        
        # 启动数据接收
        self.serial_bridge.start_receiving(self.feedback_callback)
        
        # 控制参数
        self.current_3508_gear = 0  # 停止
        self.current_2006_gear = 0  # 停止
        
        self.get_logger().info("Motor Controller Node initialized")
    
    def cmd_vel_callback(self, msg: Twist):
        """
        cmd_vel话题回调函数
        将geometry_msgs/Twist消息转换为电机控制命令
        """
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # 根据线速度控制3508电机
        if linear_x == 0:
            gear_3508 = 0  # 停止
        elif abs(linear_x) <= 0.3:
            gear_3508 = 1  # 低速
        elif abs(linear_x) <= 0.6:
            gear_3508 = 2  # 中速
        else:
            gear_3508 = 3  # 高速
        
        # 根据角速度控制2006电机
        if angular_z == 0:
            gear_2006 = 0  # 停止
        elif abs(angular_z) <= 0.5:
            gear_2006 = 1  # 低速
        elif abs(angular_z) <= 1.0:
            gear_2006 = 2  # 中速
        else:
            gear_2006 = 3  # 高速
        
        # 发送控制命令
        if gear_3508 != self.current_3508_gear:
            self.serial_bridge.send_motor_control(0x01, gear_3508)
            self.current_3508_gear = gear_3508
        
        if gear_2006 != self.current_2006_gear:
            self.serial_bridge.send_motor_control(0x02, gear_2006)
            self.current_2006_gear = gear_2006
    
    def handle_3508_control(self, request: Trigger.Request, response: Trigger.Response):
        """3508电机控制服务"""
        try:
            # 循环切换档位
            self.current_3508_gear = (self.current_3508_gear + 1) % 4
            success = self.serial_bridge.send_motor_control(0x01, self.current_3508_gear)
            
            gear_names = ["STOP", "LOW", "MID", "HIGH"]
            response.success = success
            response.message = f"3508 motor set to {gear_names[self.current_3508_gear]} gear"
            
        except Exception as e:
            response.success = False
            response.message = f"Failed to control 3508 motor: {e}"
        
        return response
    
    def handle_2006_control(self, request: Trigger.Request, response: Trigger.Response):
        """2006电机控制服务"""
        try:
            # 循环切换档位
            self.current_2006_gear = (self.current_2006_gear + 1) % 4
            success = self.serial_bridge.send_motor_control(0x02, self.current_2006_gear)
            
            gear_names = ["STOP", "LOW", "MID", "HIGH"]
            response.success = success
            response.message = f"2006 motor set to {gear_names[self.current_2006_gear]} gear"
            
        except Exception as e:
            response.success = False
            response.message = f"Failed to control 2006 motor: {e}"
        
        return response
    
    def feedback_callback(self, data: bytes):
        """反馈数据回调函数"""
        # 这里可以处理STM32发回的反馈数据
        self.get_logger().debug(f"Received feedback: {data.hex()}")
    
    def destroy_node(self):
        """重写销毁方法，确保资源清理"""
        self.get_logger().info("Shutting down Motor Controller Node")
        # 发送停止命令
        self.serial_bridge.send_motor_control(0x01, 0)  # 停止3508
        self.serial_bridge.send_motor_control(0x02, 0)  # 停止2006
        # 断开串口
        self.serial_bridge.disconnect()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    
    node = MotorControllerNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()