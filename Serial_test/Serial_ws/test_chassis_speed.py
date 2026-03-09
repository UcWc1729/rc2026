#!/usr/bin/env python3
"""
@file test_chassis_speed.py
@brief 测试底盘速度控制 - 直接发送 Vx=0.1, Vy=0, Wz=0
@date 2026-01-23
"""

import sys
import os

# 添加源码路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'my_package_py'))

from my_package_py.protocol_handler import ProtocolHandler
import serial
import time


def main():
    """测试函数"""
    
    # 配置参数
    SERIAL_PORT = '/dev/ttyUSB0'
    BAUDRATE = 115200
    
    print("=" * 70)
    print("底盘速度控制测试")
    print("=" * 70)
    print(f"串口: {SERIAL_PORT}")
    print(f"波特率: {BAUDRATE}")
    print(f"命令: Vx=0.1 m/s, Vy=0 m/s, Wz=0 rad/s")
    print("=" * 70)
    
    # 创建协议处理器
    protocol = ProtocolHandler()
    
    # 打包速度命令
    vx, vy, wz = 0.1, 0.0, 0.0
    frame = protocol.pack_chassis_speed(vx, vy, wz)
    
    # 打印帧信息
    print(f"\n📦 生成的数据帧:")
    print(f"  总长度: {len(frame)} 字节")
    print(f"  十六进制: {frame.hex()}")
    print(f"  详细结构:")
    print(f"    - SOF (帧头):        0x{frame[0]:02X}")
    print(f"    - 数据长度:          {int.from_bytes(frame[1:3], 'little')} 字节")
    print(f"    - 序列号:            {frame[3]}")
    print(f"    - CRC8:              0x{frame[4]:02X}")
    print(f"    - 命令ID:            0x{int.from_bytes(frame[5:7], 'little'):04X}")
    print(f"    - 数据段 (12字节):   {frame[7:19].hex()}")
    print(f"    - CRC16:             0x{int.from_bytes(frame[19:21], 'little'):04X}")
    
    # 连接串口
    print(f"\n🔌 连接串口 {SERIAL_PORT}...")
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=0.1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        print("✓ 串口连接成功")
    except Exception as e:
        print(f"✗ 串口连接失败: {e}")
        print("\n提示: 请检查:")
        print("  1. 串口设备是否存在 (ls /dev/tty*)")
        print("  2. 是否有权限访问串口 (sudo chmod 666 /dev/ttyUSB0)")
        print("  3. 串口是否被其他程序占用")
        return
    
    # 发送数据
    print(f"\n📤 发送数据...")
    try:
        ser.write(frame)
        ser.flush()
        print(f"✓ 成功发送 {len(frame)} 字节")
        
        # 等待可能的回复
        time.sleep(0.1)
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"\n📥 接收到回复 ({len(response)} 字节):")
            print(f"  十六进制: {response.hex()}")
            
            # 尝试解析
            success, cmd_id, data, seq = protocol.parse_frame(response)
            if success:
                print(f"  ✓ 解析成功:")
                print(f"    - 命令ID: 0x{cmd_id:04X}")
                print(f"    - 序列号: {seq}")
                print(f"    - 数据长度: {len(data)} 字节")
            else:
                print("  ⚠ 解析失败")
        else:
            print("  (无回复数据)")
            
    except Exception as e:
        print(f"✗ 发送失败: {e}")
    finally:
        ser.close()
        print("\n🔒 串口已关闭")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
