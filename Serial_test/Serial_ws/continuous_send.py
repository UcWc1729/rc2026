#!/usr/bin/env python3
"""
@file continuous_send.py
@brief 持续发送底盘速度控制命令 - 用于测试电机转动
@date 2026-01-23
"""

import sys
import os
import time
import signal

# 添加源码路径到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'my_package_py'))

from my_package_py.protocol_handler import ProtocolHandler
import serial


class ContinuousSender:
    """持续发送速度命令"""
    
    def __init__(self, serial_port='/dev/ttyUSB0', baudrate=115200):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.protocol = ProtocolHandler()
        self.ser = None
        self.running = False
        
        # 速度参数（可修改）
        self.vx = 0.1
        self.vy = 0.0
        self.wz = 0.0
        self.send_rate = 50  # Hz
        
    def connect(self):
        """连接串口"""
        try:
            self.ser = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print(f"✓ 串口连接成功: {self.serial_port}")
            return True
        except Exception as e:
            print(f"✗ 串口连接失败: {e}")
            return False
    
    def send_speed(self):
        """发送速度命令"""
        frame = self.protocol.pack_chassis_speed(self.vx, self.vy, self.wz)
        try:
            self.ser.write(frame)
            self.ser.flush()
            return True
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def run(self):
        """持续发送"""
        self.running = True
        send_interval = 1.0 / self.send_rate
        send_count = 0
        start_time = time.time()
        
        print("\n开始持续发送速度命令...")
        print("按 Ctrl+C 停止\n")
        
        try:
            while self.running:
                if self.send_speed():
                    send_count += 1
                    elapsed = time.time() - start_time
                    
                    # 每秒打印一次状态
                    if send_count % self.send_rate == 0:
                        print(f"[{elapsed:.1f}s] 已发送 {send_count} 帧 "
                              f"| 速度: Vx={self.vx:.2f}, Vy={self.vy:.2f}, Wz={self.wz:.2f}")
                
                time.sleep(send_interval)
                
        except KeyboardInterrupt:
            print("\n\n收到停止信号...")
        finally:
            self.stop()
            
    def stop(self):
        """停止并发送零速度"""
        self.running = False
        print("\n发送停止命令（零速度）...")
        
        # 发送零速度
        self.vx, self.vy, self.wz = 0.0, 0.0, 0.0
        for _ in range(3):
            self.send_speed()
            time.sleep(0.02)
        
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        print("✓ 串口已关闭")


def print_banner():
    """打印启动横幅"""
    print("=" * 70)
    print("🔄 持续发送底盘速度控制命令")
    print("=" * 70)
    print()


def print_config(sender):
    """打印配置信息"""
    print("📊 配置信息:")
    print(f"  串口:     {sender.serial_port}")
    print(f"  波特率:   {sender.baudrate}")
    print(f"  发送频率: {sender.send_rate} Hz")
    print()
    print("🎯 速度参数:")
    print(f"  Vx (前进): {sender.vx:.3f} m/s")
    print(f"  Vy (横移): {sender.vy:.3f} m/s")
    print(f"  Wz (旋转): {sender.wz:.3f} rad/s")
    print()
    
    # 显示生成的帧
    frame = sender.protocol.pack_chassis_speed(sender.vx, sender.vy, sender.wz)
    print("📦 数据帧信息:")
    print(f"  长度:     {len(frame)} 字节")
    print(f"  十六进制: {frame.hex()}")
    print()


def main():
    """主函数"""
    print_banner()
    
    # 创建发送器
    sender = ContinuousSender(
        serial_port='/dev/ttyUSB0',
        baudrate=115200
    )
    
    # 设置速度参数（在这里修改速度值）
    sender.vx = 0.1    # 前进速度 (m/s)
    sender.vy = 0.0    # 横向速度 (m/s)
    sender.wz = 0.0    # 旋转速度 (rad/s)
    sender.send_rate = 50  # 发送频率 (Hz)
    
    print_config(sender)
    
    # 连接串口
    print("🔌 连接串口...")
    if not sender.connect():
        print("\n提示:")
        print("  1. 检查串口设备: ls /dev/ttyUSB*")
        print("  2. 添加权限: sudo chmod 666 /dev/ttyUSB0")
        print("  3. 或运行: ./quick_test.sh")
        return
    
    print()
    print("=" * 70)
    
    # 开始持续发送
    sender.run()
    
    print("\n" + "=" * 70)
    print("✓ 程序已退出")
    print("=" * 70)


if __name__ == '__main__':
    main()
