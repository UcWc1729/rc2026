#!/usr/bin/env python3
"""
@file serial_bridge.py
@brief 串口通信桥接模块 - 负责与STM32的通信 (ROS2版本)
"""

import serial
import struct
import threading
import rclpy
from rclpy.node import Node
from typing import Optional, Callable

class SerialBridge:
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
        """
        构建控制数据包 (与STM32协议完全一致)
        
        数据包格式 (7字节):
        +--------+--------+------------+------+-------+-------+--------+
        | Header | Header | Motor_Type | Gear | CRC16 | CRC16 | Footer |
        | 0xAA55 | (2B)   | (1B)       | (1B) | Low   | High  | 0x0D   |
        +--------+--------+------------+------+-------+-------+--------+
        
        Args:
            motor_type: 电机类型 (0x01=3508, 0x02=2006)
            gear: 档位 (0x00=停止, 0x01=低速, 0x02=中速, 0x03=高速)
        
        Returns:
            bytes: 7字节数据包
        """
        # 构建数据包
        packet = bytearray()
        
        # 帧头 (2字节) - 小端序: 0xAA55 -> [0x55, 0xAA]
        packet.extend(struct.pack('<H', self.PROTOCOL_HEADER))
        
        # 电机类型 + 档位 (2字节)
        packet.extend(struct.pack('BB', motor_type, gear))
        
        # 计算CRC16 - 对帧头+电机类型+档位计算 (4字节)
        crc_data = packet[0:4]  # header(2) + motor_type(1) + gear(1)
        crc = self.calculate_crc16(crc_data)
        
        # CRC16 (2字节) - 小端序
        packet.extend(struct.pack('<H', crc))
        
        # 帧尾 (1字节)
        packet.extend(struct.pack('B', self.PROTOCOL_FOOTER))
        
        return bytes(packet)
    
    def send_motor_control(self, motor_type: int, gear: int) -> bool:
        """
        发送电机控制命令
        
        Args:
            motor_type: 电机类型
            gear: 档位
        
        Returns:
            bool: 发送成功返回True，失败返回False
        """
        if not self.is_connected or not self.ser:
            self.node.get_logger().warn("Serial port not connected")
            return False
        
        try:
            packet = self.build_control_packet(motor_type, gear)
            self.ser.write(packet)
            
            # 打印调试信息
            motor_name = "3508" if motor_type == 0x01 else "2006"
            gear_names = ["STOP", "LOW", "MID", "HIGH"]
            gear_name = gear_names[gear] if gear < len(gear_names) else "UNKNOWN"
            
            self.node.get_logger().info(f"Sent control: Motor={motor_name}, Gear={gear_name}")
            
            # 打印原始数据包 (调试用)
            hex_str = ' '.join([f'{b:02X}' for b in packet])
            self.node.get_logger().debug(f"Raw packet: {hex_str}")
            
            return True
            
        except Exception as e:
            self.node.get_logger().error(f"Failed to send motor control: {e}")
            return False
    
    def start_receiving(self, callback: Callable):
        """
        启动数据接收线程
        
        Args:
            callback: 数据接收回调函数
        """
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
        expected_length = 7  # STM32返回数据包固定7字节
        
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
                            # 完整数据包接收完成
                            if self.receive_callback:
                                self.receive_callback(packet_buffer)
                            state = 'header1'
                            packet_buffer = bytearray()
                            
            except Exception as e:
                self.node.get_logger().error(f"Error in receive loop: {e}")
                state = 'header1'
                packet_buffer = bytearray()