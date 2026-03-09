#!/usr/bin/env python3
"""
@file protocol_handler.py
@brief 通用上下位机通信协议处理类（与Serial_test版本完全一致）
@version 1.0
@date 2026-01-23
"""

import struct
from typing import Tuple, Optional


class ProtocolHandler:
    """协议处理类 - 实现帧打包和解析"""
    
    # 协议常量
    SOF = 0xA5
    MAX_DATA_LENGTH = 512
    
    # 命令ID定义
    CMD_CHASSIS_SPEED = 0x0101
    CMD_CHASSIS_STOP = 0x0102
    CMD_CHASSIS_FEEDBACK = 0x8101
    CMD_HEARTBEAT = 0x0FFF
    CMD_ERROR_REPORT = 0xFE00
    
    def __init__(self):
        self.tx_seq = 0
        
    @staticmethod
    def crc8_calculate(data: bytes) -> int:
        """计算CRC8校验值"""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc <<= 1
                crc &= 0xFF
        return crc
    
    @staticmethod
    def crc16_calculate(data: bytes) -> int:
        """计算CRC16校验值 (MODBUS)"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF
    
    def pack_frame(self, cmd_id: int, data: bytes) -> bytes:
        """
        打包数据帧
        
        Args:
            cmd_id: 命令ID
            data: 数据内容
            
        Returns:
            完整的帧数据
        """
        payload_len = 2 + len(data)  # cmd_id(2) + data
        
        # 1. 构建帧头部分（不含CRC8）
        header_partial = struct.pack('<HB', payload_len, self.tx_seq)
        
        # 2. 计算帧头CRC8（对data_length和seq共3字节）
        crc8 = self.crc8_calculate(header_partial)
        
        # 3. 完整帧头
        header = struct.pack('<BHBB', self.SOF, payload_len, self.tx_seq, crc8)
        
        # 4. 命令ID + 数据段
        payload = struct.pack('<H', cmd_id) + data
        
        # 5. 计算整帧CRC16
        frame_without_crc = header + payload
        crc16 = self.crc16_calculate(frame_without_crc)
        
        # 6. 完整帧
        frame = frame_without_crc + struct.pack('<H', crc16)
        
        # 7. 序列号自增
        self.tx_seq = (self.tx_seq + 1) & 0xFF
        
        return frame
    
    def pack_chassis_speed(self, vx: float, vy: float, wz: float) -> bytes:
        """
        打包底盘速度控制命令
        
        Args:
            vx: X方向速度 (m/s)
            vy: Y方向速度 (m/s)
            wz: 旋转角速度 (rad/s)
            
        Returns:
            完整的帧数据
        """
        data = struct.pack('<fff', vx, vy, wz)
        return self.pack_frame(self.CMD_CHASSIS_SPEED, data)
    
    def pack_chassis_stop(self) -> bytes:
        """
        打包底盘急停命令
        
        Returns:
            完整的帧数据
        """
        return self.pack_frame(self.CMD_CHASSIS_STOP, b'')
    
    def pack_heartbeat(self, timestamp: int) -> bytes:
        """
        打包心跳包
        
        Args:
            timestamp: 时间戳 (ms)
            
        Returns:
            完整的帧数据
        """
        data = struct.pack('<IB', timestamp, 0xAA)
        return self.pack_frame(self.CMD_HEARTBEAT, data)
    
    def parse_frame(self, buffer: bytes) -> Tuple[bool, int, bytes, int]:
        """
        解析数据帧
        
        Args:
            buffer: 接收到的数据
            
        Returns:
            (success, cmd_id, data, seq)
        """
        # 1. 检查最小长度
        if len(buffer) < 9:
            return (False, 0, b'', 0)
        
        # 2. 检查帧头标志
        if buffer[0] != self.SOF:
            return (False, 0, b'', 0)
        
        # 3. 解析帧头
        sof, payload_len, seq, crc8_recv = struct.unpack('<BHBB', buffer[:5])
        
        # 4. 验证帧头CRC8
        crc8_calc = self.crc8_calculate(struct.pack('<HB', payload_len, seq))
        if crc8_calc != crc8_recv:
            return (False, 0, b'', 0)
        
        # 5. 检查长度
        expected_len = 5 + payload_len + 2
        if len(buffer) < expected_len:
            return (False, 0, b'', 0)
        
        # 6. 验证整帧CRC16
        crc16_calc = self.crc16_calculate(buffer[:expected_len-2])
        crc16_recv = struct.unpack('<H', buffer[expected_len-2:expected_len])[0]
        if crc16_calc != crc16_recv:
            return (False, 0, b'', 0)
        
        # 7. 提取命令ID和数据
        cmd_id = struct.unpack('<H', buffer[5:7])[0]
        data = buffer[7:expected_len-2]
        
        return (True, cmd_id, data, seq)
    
    def parse_chassis_feedback(self, data: bytes) -> Optional[dict]:
        """
        解析底盘反馈数据
        
        Args:
            data: 数据段
            
        Returns:
            解析后的字典，失败返回None
        """
        if len(data) != 33:  # 4+4+4+4+16+1
            return None
        
        unpacked = struct.unpack('<IffffffB', data[:33])
        
        return {
            'timestamp': unpacked[0],
            'velocity_x': unpacked[1],
            'velocity_y': unpacked[2],
            'angular_vel': unpacked[3],
            'motor_speed': [unpacked[4], unpacked[5], unpacked[6], unpacked[7]],
            'status': unpacked[8]
        }
