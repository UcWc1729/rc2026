#!/usr/bin/env python3
"""
@file diagnose_serial.py
@brief 串口通信诊断工具 - 检查为什么电机不转
@date 2026-01-23
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'my_package_py'))

from my_package_py.protocol_handler import ProtocolHandler
import serial
import struct


def print_header(text):
    """打印分隔符"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def test_crc_compatibility():
    """测试CRC计算是否与C代码兼容"""
    print_header("1. CRC校验兼容性测试")
    
    protocol = ProtocolHandler()
    
    # 测试CRC8
    test_data = bytes([0x0E, 0x00, 0x00])  # data_length=14, seq=0
    crc8 = protocol.crc8_calculate(test_data)
    print(f"CRC8测试:")
    print(f"  输入数据: {test_data.hex()}")
    print(f"  CRC8结果: 0x{crc8:02X}")
    print(f"  预期值: 0xBC")
    print(f"  状态: {'✓ 通过' if crc8 == 0xBC else '✗ 失败'}")
    
    # 测试CRC16
    print(f"\nCRC16测试:")
    test_frame = bytes.fromhex('a50e0000bc0101cdcccc3d00000000000000')
    crc16 = protocol.crc16_calculate(test_frame)
    print(f"  CRC16结果: 0x{crc16:04X}")
    print(f"  预期值: 0x7872")
    print(f"  状态: {'✓ 通过' if crc16 == 0x7872 else '✗ 失败'}")


def test_frame_structure():
    """测试数据帧结构"""
    print_header("2. 数据帧结构测试")
    
    protocol = ProtocolHandler()
    frame = protocol.pack_chassis_speed(0.1, 0.0, 0.0)
    
    print(f"生成的数据帧:")
    print(f"  完整帧 (hex): {frame.hex()}")
    print(f"  总长度: {len(frame)} 字节")
    print()
    
    # 逐字节解析
    print("逐字节解析:")
    print(f"  [0] SOF:           0x{frame[0]:02X} {'✓' if frame[0] == 0xA5 else '✗'}")
    print(f"  [1-2] DataLen:     {struct.unpack('<H', frame[1:3])[0]} (0x{frame[1:3].hex()}) {'✓' if struct.unpack('<H', frame[1:3])[0] == 14 else '✗'}")
    print(f"  [3] Seq:           {frame[3]} (0x{frame[3]:02X})")
    print(f"  [4] CRC8:          0x{frame[4]:02X}")
    print(f"  [5-6] CMD_ID:      0x{struct.unpack('<H', frame[5:7])[0]:04X} {'✓' if struct.unpack('<H', frame[5:7])[0] == 0x0101 else '✗'}")
    print(f"  [7-10] Vx:         {struct.unpack('<f', frame[7:11])[0]:.6f} {'✓' if abs(struct.unpack('<f', frame[7:11])[0] - 0.1) < 0.001 else '✗'}")
    print(f"  [11-14] Vy:        {struct.unpack('<f', frame[11:15])[0]:.6f} ✓")
    print(f"  [15-18] Wz:        {struct.unpack('<f', frame[15:19])[0]:.6f} ✓")
    print(f"  [19-20] CRC16:     0x{struct.unpack('<H', frame[19:21])[0]:04X}")
    
    # 与协议文档对比
    print()
    print("与协议文档对比:")
    expected = "a50e0000bc0101cdcccc3d00000000000000007278"
    actual = frame.hex()
    print(f"  协议文档示例: {expected}")
    print(f"  实际生成帧:   {actual}")
    print(f"  状态: {'✓ 完全匹配' if expected == actual else '✗ 不匹配'}")


def test_serial_connection(port='/dev/ttyUSB0', baudrate=115200):
    """测试串口连接"""
    print_header("3. 串口连接测试")
    
    print(f"串口设备: {port}")
    print(f"波特率: {baudrate}")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        print(f"✓ 串口连接成功")
        print(f"  设备: {ser.name}")
        print(f"  波特率: {ser.baudrate}")
        print(f"  数据位: {ser.bytesize}")
        print(f"  停止位: {ser.stopbits}")
        print(f"  校验位: {ser.parity}")
        
        ser.close()
        return True
    except Exception as e:
        print(f"✗ 串口连接失败: {e}")
        return False


def test_send_receive(port='/dev/ttyUSB0', baudrate=115200):
    """测试发送和接收"""
    print_header("4. 发送/接收测试")
    
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.5)
        protocol = ProtocolHandler()
        
        # 发送测试帧
        frame = protocol.pack_chassis_speed(0.1, 0.0, 0.0)
        print(f"发送数据帧:")
        print(f"  数据: {frame.hex()}")
        print(f"  长度: {len(frame)} 字节")
        
        ser.write(frame)
        ser.flush()
        print(f"✓ 发送成功")
        
        # 等待接收
        print(f"\n等待下位机回复...")
        time.sleep(0.2)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"✓ 收到回复:")
            print(f"  长度: {len(response)} 字节")
            print(f"  数据: {response.hex()}")
            
            # 尝试解析
            success, cmd_id, data, seq = protocol.parse_frame(response)
            if success:
                print(f"  解析成功:")
                print(f"    命令ID: 0x{cmd_id:04X}")
                print(f"    序列号: {seq}")
                print(f"    数据长度: {len(data)} 字节")
            else:
                print(f"  ⚠ 解析失败（可能不是标准帧）")
        else:
            print(f"⚠ 未收到回复")
            print(f"  可能原因:")
            print(f"    1. 下位机未运行")
            print(f"    2. 下位机未实现反馈")
            print(f"    3. 串口TX/RX接反")
        
        ser.close()
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")


def test_continuous_send(port='/dev/ttyUSB0', baudrate=115200, duration=3):
    """测试持续发送"""
    print_header("5. 持续发送测试")
    
    try:
        ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.1)
        protocol = ProtocolHandler()
        
        print(f"持续发送 {duration} 秒...")
        print(f"速度: Vx=0.1, Vy=0.0, Wz=0.0")
        print(f"频率: 50 Hz")
        print()
        
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < duration:
            frame = protocol.pack_chassis_speed(0.1, 0.0, 0.0)
            ser.write(frame)
            ser.flush()
            count += 1
            time.sleep(0.02)  # 50Hz
            
            if count % 50 == 0:
                elapsed = time.time() - start_time
                print(f"  [{elapsed:.1f}s] 已发送 {count} 帧")
        
        print(f"\n✓ 发送完成")
        print(f"  总发送: {count} 帧")
        print(f"  平均频率: {count/duration:.1f} Hz")
        
        # 发送停止命令
        print(f"\n发送停止命令...")
        for _ in range(5):
            frame = protocol.pack_chassis_speed(0.0, 0.0, 0.0)
            ser.write(frame)
            ser.flush()
            time.sleep(0.02)
        print(f"✓ 停止命令已发送")
        
        ser.close()
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")


def check_downstream_issues():
    """检查下位机可能的问题"""
    print_header("6. 下位机问题检查清单")
    
    print("请检查以下项目:")
    print()
    print("□ 1. 下位机程序是否正常运行?")
    print("     - 检查LED指示灯")
    print("     - 使用调试器查看程序状态")
    print()
    print("□ 2. protocol_chassis.c 是否正确集成?")
    print("     - Protocol_Init() 是否调用")
    print("     - Protocol_RegisterCallbacks() 是否注册回调")
    print("     - UART接收中断是否调用 Protocol_ProcessData()")
    print()
    print("□ 3. 串口配置是否正确?")
    print("     - 波特率: 115200")
    print("     - 数据位: 8")
    print("     - 停止位: 1")
    print("     - 校验: None")
    print()
    print("□ 4. 在回调函数中添加调试输出:")
    print("     void handle_chassis_speed(float vx, float vy, float wz) {")
    print("         printf(\"收到速度: vx=%.2f, vy=%.2f, wz=%.2f\\n\", vx, vy, wz);")
    print("         // 控制电机...")
    print("     }")
    print()
    print("□ 5. 电机驱动是否正常?")
    print("     - 电机使能是否打开")
    print("     - PWM输出是否正常")
    print("     - 电源供电是否充足")
    print()
    print("□ 6. 使用串口助手查看原始数据")
    print("     - 确认是否收到数据")
    print("     - 查看数据格式是否正确")
    print()
    print("□ 7. 检查CRC校验")
    print("     - 在Protocol_ParseFrame中添加调试输出")
    print("     - 查看CRC8和CRC16是否校验通过")


def suggest_solutions():
    """建议解决方案"""
    print_header("7. 故障排除建议")
    
    print("如果电机仍不转动，请尝试:")
    print()
    print("方案1: 增加速度值")
    print("  - 当前速度可能太小（0.1 m/s）")
    print("  - 尝试: sender.vx = 0.5 或更大")
    print()
    print("方案2: 检查下位机调试输出")
    print("  - 在STM32中添加printf调试")
    print("  - 确认是否收到并解析数据")
    print()
    print("方案3: 使用串口助手验证")
    print("  - 发送相同的数据帧")
    print("  - 对比结果")
    print()
    print("方案4: 简化测试")
    print("  - 先不使用协议")
    print("  - 直接发送简单命令测试电机")
    print()
    print("方案5: 硬件检查")
    print("  - TX/RX是否接反")
    print("  - 电平是否匹配（3.3V vs 5V）")
    print("  - 是否需要电平转换芯片")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  🔍 串口通信诊断工具")
    print("=" * 70)
    print("\n此工具将帮助诊断为什么电机不转动\n")
    
    # 1. CRC兼容性测试
    test_crc_compatibility()
    
    # 2. 数据帧结构测试
    test_frame_structure()
    
    # 3. 串口连接测试
    serial_ok = test_serial_connection()
    
    if not serial_ok:
        print("\n⚠ 串口连接失败，请先解决串口问题")
        print("  提示: sudo chmod 666 /dev/ttyUSB0")
        return
    
    # 4. 发送接收测试
    test_send_receive()
    
    # 5. 持续发送测试
    print("\n是否进行持续发送测试? (y/n): ", end='', flush=True)
    try:
        choice = input().strip().lower()
        if choice == 'y':
            test_continuous_send(duration=3)
    except:
        pass
    
    # 6. 下位机检查清单
    check_downstream_issues()
    
    # 7. 解决方案建议
    suggest_solutions()
    
    print("\n" + "=" * 70)
    print("  诊断完成")
    print("=" * 70)
    print()


if __name__ == '__main__':
    main()
