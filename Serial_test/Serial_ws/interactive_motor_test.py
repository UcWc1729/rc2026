#!/usr/bin/env python3
"""
@file interactive_motor_test.py
@brief 交互式电机测试 - 可以实时修改速度参数
@date 2026-01-23
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'my_package_py'))

from my_package_py.protocol_handler import ProtocolHandler
import serial


class InteractiveMotorTest:
    """交互式电机测试"""
    
    def __init__(self, serial_port='/dev/ttyUSB0', baudrate=115200):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.protocol = ProtocolHandler()
        self.ser = None
        
        # 速度参数
        self.vx = 0.0
        self.vy = 0.0
        self.wz = 0.0
        self.send_rate = 50  # Hz
        
        # 控制标志
        self.running = False
        self.send_thread = None
        self.send_count = 0
        self.start_time = 0
        
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
    
    def send_loop(self):
        """发送循环（后台线程）"""
        send_interval = 1.0 / self.send_rate
        last_print_time = time.time()
        first_frame_sent = False
        
        while self.running:
            frame = self.protocol.pack_chassis_speed(self.vx, self.vy, self.wz)
            try:
                self.ser.write(frame)
                self.ser.flush()
                self.send_count += 1
                
                # 打印第一帧详情用于调试
                if not first_frame_sent:
                    print(f"\n📤 第一帧: {frame.hex()}")
                    print(f"   长度: {len(frame)} 字节")
                    first_frame_sent = True
                
                # 每秒打印一次状态（不干扰用户输入）
                current_time = time.time()
                if current_time - last_print_time >= 1.0:
                    elapsed = current_time - self.start_time
                    print(f"\r[运行 {elapsed:.0f}s] 已发送 {self.send_count} 帧 | "
                          f"速度: Vx={self.vx:.2f}, Vy={self.vy:.2f}, Wz={self.wz:.2f}  ",
                          end='', flush=True)
                    last_print_time = current_time
                
            except Exception as e:
                print(f"\n发送失败: {e}")
                break
            
            time.sleep(send_interval)
    
    def start_sending(self):
        """开始发送"""
        if not self.running:
            self.running = True
            self.send_count = 0
            self.start_time = time.time()
            self.send_thread = threading.Thread(target=self.send_loop, daemon=True)
            self.send_thread.start()
            print("\n✓ 开始发送速度命令...")
    
    def stop_sending(self):
        """停止发送"""
        if self.running:
            print("\n\n⏸ 停止发送...")
            self.running = False
            if self.send_thread:
                self.send_thread.join(timeout=1.0)
            
            # 发送零速度
            self.vx = self.vy = self.wz = 0.0
            for _ in range(3):
                frame = self.protocol.pack_chassis_speed(0, 0, 0)
                self.ser.write(frame)
                self.ser.flush()
                time.sleep(0.02)
            
            print("✓ 已发送停止命令（零速度）")
    
    def close(self):
        """关闭连接"""
        self.stop_sending()
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✓ 串口已关闭")
    
    def print_menu(self):
        """打印菜单"""
        print("\n" + "=" * 60)
        print("📋 命令菜单:")
        print("-" * 60)
        print("  1 - 前进测试  (Vx=0.1)")
        print("  2 - 后退测试  (Vx=-0.1)")
        print("  3 - 左移测试  (Vy=0.1)")
        print("  4 - 右移测试  (Vy=-0.1)")
        print("  5 - 左转测试  (Wz=0.5)")
        print("  6 - 右转测试  (Wz=-0.5)")
        print("  7 - 自定义速度")
        print("  8 - 显示当前速度")
        print("  s - 开始/继续发送")
        print("  p - 暂停发送")
        print("  0 - 停止电机（零速度）")
        print("  q - 退出程序")
        print("=" * 60)
    
    def run_interactive(self):
        """交互式运行"""
        print("\n" + "=" * 60)
        print("🎮 交互式电机测试模式")
        print("=" * 60)
        print(f"串口: {self.serial_port} @ {self.baudrate}")
        print(f"发送频率: {self.send_rate} Hz")
        
        self.print_menu()
        
        while True:
            try:
                print("\n请输入命令: ", end='', flush=True)
                cmd = input().strip().lower()
                
                if cmd == '1':
                    self.vx, self.vy, self.wz = 0.1, 0.0, 0.0
                    print("✓ 设置为前进: Vx=0.1")
                    
                elif cmd == '2':
                    self.vx, self.vy, self.wz = -0.1, 0.0, 0.0
                    print("✓ 设置为后退: Vx=-0.1")
                    
                elif cmd == '3':
                    self.vx, self.vy, self.wz = 0.0, 0.1, 0.0
                    print("✓ 设置为左移: Vy=0.1")
                    
                elif cmd == '4':
                    self.vx, self.vy, self.wz = 0.0, -0.1, 0.0
                    print("✓ 设置为右移: Vy=-0.1")
                    
                elif cmd == '5':
                    self.vx, self.vy, self.wz = 0.0, 0.0, 0.5
                    print("✓ 设置为左转: Wz=0.5")
                    
                elif cmd == '6':
                    self.vx, self.vy, self.wz = 0.0, 0.0, -0.5
                    print("✓ 设置为右转: Wz=-0.5")
                    
                elif cmd == '7':
                    print("输入 Vx (m/s): ", end='')
                    self.vx = float(input().strip())
                    print("输入 Vy (m/s): ", end='')
                    self.vy = float(input().strip())
                    print("输入 Wz (rad/s): ", end='')
                    self.wz = float(input().strip())
                    print(f"✓ 自定义速度: Vx={self.vx}, Vy={self.vy}, Wz={self.wz}")
                    
                elif cmd == '8':
                    print(f"当前速度: Vx={self.vx:.3f}, Vy={self.vy:.3f}, Wz={self.wz:.3f}")
                    print(f"发送状态: {'运行中' if self.running else '已停止'}")
                    if self.running:
                        print(f"已发送: {self.send_count} 帧")
                    
                elif cmd == 's':
                    if not self.running:
                        self.start_sending()
                    else:
                        print("已在发送中...")
                    
                elif cmd == 'p':
                    self.stop_sending()
                    
                elif cmd == '0':
                    self.vx = self.vy = self.wz = 0.0
                    print("✓ 设置为零速度（停止）")
                    if not self.running:
                        # 如果没在发送，立即发送停止命令
                        for _ in range(3):
                            frame = self.protocol.pack_chassis_speed(0, 0, 0)
                            self.ser.write(frame)
                            self.ser.flush()
                            time.sleep(0.02)
                        print("✓ 已发送停止命令")
                    
                elif cmd == 'q':
                    print("\n退出程序...")
                    break
                    
                elif cmd == 'h' or cmd == 'help':
                    self.print_menu()
                    
                else:
                    print("未知命令，输入 'h' 查看帮助")
                    
            except ValueError:
                print("✗ 输入错误，请输入有效的数字")
            except KeyboardInterrupt:
                print("\n\n收到中断信号...")
                break
            except Exception as e:
                print(f"错误: {e}")
        
        self.close()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🎮 交互式电机测试程序")
    print("=" * 60)
    
    tester = InteractiveMotorTest(
        serial_port='/dev/ttyUSB0',
        baudrate=115200
    )
    
    print("\n🔌 连接串口...")
    if not tester.connect():
        print("\n提示:")
        print("  1. 检查串口设备: ls /dev/ttyUSB*")
        print("  2. 添加权限: sudo chmod 666 /dev/ttyUSB0")
        return
    
    tester.run_interactive()
    
    print("\n" + "=" * 60)
    print("✓ 程序已退出")
    print("=" * 60)


if __name__ == '__main__':
    main()
