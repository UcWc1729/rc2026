#!/usr/bin/env python3
"""
@file simple_motor_test.py
@brief 简化版电机测试 - 主线程直接发送（与diagnose_serial.py相同逻辑）
@date 2026-01-23
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'my_package_py'))

from my_package_py.protocol_handler import ProtocolHandler
import serial


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🔧 简化版电机测试 - 主线程发送")
    print("=" * 60)
    print("\n此版本使用与diagnose_serial.py相同的发送逻辑")
    print("如果诊断工具能工作，这个也应该能工作\n")
    
    # 连接串口
    port = '/dev/ttyUSB0'
    baudrate = 115200
    
    print(f"连接串口: {port} @ {baudrate}...")
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        print("✓ 串口连接成功\n")
    except Exception as e:
        print(f"✗ 串口连接失败: {e}")
        print("  提示: sudo chmod 666 /dev/ttyUSB0")
        return
    
    protocol = ProtocolHandler()
    
    # 菜单
    print("=" * 60)
    print("📋 测试菜单:")
    print("-" * 60)
    print("  1 - 前进 (Vx=0.1)     2 - 后退 (Vx=-0.1)")
    print("  3 - 左移 (Vy=0.1)     4 - 右移 (Vy=-0.1)")
    print("  5 - 左转 (Wz=0.5)     6 - 右转 (Wz=-0.5)")
    print("  7 - 前进快 (Vx=1.0)   8 - 自定义速度")
    print("  0 - 停止电机          q - 退出")
    print("=" * 60)
    
    try:
        while True:
            print("\n请选择测试 (按回车确认): ", end='', flush=True)
            choice = input().strip()
            
            if choice == 'q':
                break
            
            # 确定速度值
            vx, vy, wz = 0.0, 0.0, 0.0
            duration = 3  # 默认发送3秒
            
            if choice == '1':
                vx = 0.1
                print("✓ 前进测试: Vx=0.1")
            elif choice == '2':
                vx = -0.1
                print("✓ 后退测试: Vx=-0.1")
            elif choice == '3':
                vy = 0.1
                print("✓ 左移测试: Vy=0.1")
            elif choice == '4':
                vy = -0.1
                print("✓ 右移测试: Vy=-0.1")
            elif choice == '5':
                wz = 0.5
                print("✓ 左转测试: Wz=0.5")
            elif choice == '6':
                wz = -0.5
                print("✓ 右转测试: Wz=-0.5")
            elif choice == '7':
                vx = 1.0
                print("✓ 快速前进: Vx=1.0")
            elif choice == '8':
                print("输入 Vx (m/s): ", end='')
                vx = float(input().strip())
                print("输入 Vy (m/s): ", end='')
                vy = float(input().strip())
                print("输入 Wz (rad/s): ", end='')
                wz = float(input().strip())
                print("输入持续时间 (秒): ", end='')
                duration = int(input().strip())
                print(f"✓ 自定义: Vx={vx}, Vy={vy}, Wz={wz}, {duration}秒")
            elif choice == '0':
                vx, vy, wz = 0.0, 0.0, 0.0
                duration = 1
                print("✓ 停止电机")
            else:
                print("⚠ 无效选择")
                continue
            
            # 发送命令（主线程直接发送，与diagnose_serial相同）
            print(f"\n开始发送: Vx={vx}, Vy={vy}, Wz={wz}")
            print(f"持续 {duration} 秒，频率 50Hz")
            
            # 生成第一帧并显示
            frame = protocol.pack_chassis_speed(vx, vy, wz)
            print(f"数据帧: {frame.hex()} ({len(frame)}字节)")
            print()
            
            start_time = time.time()
            count = 0
            send_interval = 0.02  # 50Hz
            
            while time.time() - start_time < duration:
                frame = protocol.pack_chassis_speed(vx, vy, wz)
                ser.write(frame)
                ser.flush()
                count += 1
                
                # 每50帧打印一次
                if count % 50 == 0:
                    elapsed = time.time() - start_time
                    print(f"  [{elapsed:.1f}s] 已发送 {count} 帧")
                
                time.sleep(send_interval)
            
            print(f"✓ 完成，共发送 {count} 帧\n")
            
            # 如果不是停止命令，发送停止
            if vx != 0 or vy != 0 or wz != 0:
                print("发送停止命令...")
                for _ in range(5):
                    stop_frame = protocol.pack_chassis_speed(0, 0, 0)
                    ser.write(stop_frame)
                    ser.flush()
                    time.sleep(0.02)
                print("✓ 已停止")
    
    except KeyboardInterrupt:
        print("\n\n收到中断信号...")
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        # 确保发送停止命令
        print("\n发送最终停止命令...")
        for _ in range(5):
            stop_frame = protocol.pack_chassis_speed(0, 0, 0)
            ser.write(stop_frame)
            ser.flush()
            time.sleep(0.02)
        
        ser.close()
        print("✓ 串口已关闭")
        print("\n" + "=" * 60)
        print("程序已退出")
        print("=" * 60)


if __name__ == '__main__':
    main()
