#!/usr/bin/env python3
"""
串口协议测试工具 - 用于验证数据包格式和CRC计算
"""

import struct

def calculate_crc16(data: bytes) -> int:
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

def build_control_packet(motor_type: int, gear: int) -> bytes:
    """构建控制数据包"""
    packet = bytearray()
    
    # 帧头 (2字节) - 小端序
    packet.extend(struct.pack('<H', 0xAA55))
    
    # 电机类型 + 档位
    packet.extend(struct.pack('BB', motor_type, gear))
    
    # 计算CRC16
    crc = calculate_crc16(packet[0:4])
    packet.extend(struct.pack('<H', crc))
    
    # 帧尾
    packet.extend(struct.pack('B', 0x0D))
    
    return bytes(packet)

def print_packet(packet: bytes, description: str):
    """打印数据包信息"""
    hex_str = ' '.join([f'{b:02X}' for b in packet])
    print(f"\n{description}")
    print(f"  十六进制: {hex_str}")
    print(f"  字节数: {len(packet)}")
    print(f"  帧头: 0x{packet[0]:02X}{packet[1]:02X}")
    print(f"  电机类型: 0x{packet[2]:02X} ({'3508' if packet[2] == 0x01 else '2006'})")
    print(f"  档位: 0x{packet[3]:02X} (['停止','低速','中速','高速'][packet[3]])")
    print(f"  CRC16: 0x{packet[4]:02X}{packet[5]:02X}")
    print(f"  帧尾: 0x{packet[6]:02X}")

def main():
    print("="*60)
    print("      串口协议测试 - Serial Protocol Test")
    print("="*60)
    
    # 测试所有可能的命令组合
    motors = [(0x01, '3508'), (0x02, '2006')]
    gears = [(0x00, '停止'), (0x01, '低速'), (0x02, '中速'), (0x03, '高速')]
    
    for motor_type, motor_name in motors:
        print(f"\n{'='*60}")
        print(f"  {motor_name}电机测试")
        print(f"{'='*60}")
        
        for gear, gear_name in gears:
            packet = build_control_packet(motor_type, gear)
            description = f"{motor_name} - {gear_name}"
            print_packet(packet, description)
    
    # 验证CRC计算
    print(f"\n{'='*60}")
    print("  CRC16验证")
    print(f"{'='*60}")
    
    test_data = bytes([0x55, 0xAA, 0x01, 0x01])
    crc = calculate_crc16(test_data)
    print(f"\n测试数据: {' '.join([f'{b:02X}' for b in test_data])}")
    print(f"CRC16结果: 0x{crc:04X}")
    print(f"CRC16字节序 (小端): 0x{crc & 0xFF:02X} 0x{(crc >> 8) & 0xFF:02X}")
    
    # Python发送示例
    print(f"\n{'='*60}")
    print("  Python串口发送示例")
    print(f"{'='*60}")
    
    packet_3508_low = build_control_packet(0x01, 0x01)
    hex_list = ', '.join([f'0x{b:02X}' for b in packet_3508_low])
    
    print(f"""
import serial

# 打开串口
ser = serial.Serial('/dev/ttyUSB0', 115200)

# 发送3508低速命令
packet = bytes([{hex_list}])
ser.write(packet)

ser.close()
""")

if __name__ == '__main__':
    main()
