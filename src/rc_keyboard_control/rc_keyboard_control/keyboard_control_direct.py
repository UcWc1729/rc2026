#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
直接串口键盘控制程序
不经过ROS2，直接通过串口发送协议数据控制机器人底盘
"""

import sys
import select
import termios
import tty
import threading
import time
import serial
import struct
import argparse
from typing import Optional

# 协议常量
FRAME_HEADER_SOF = 0xA5
CMD_CHASSIS_SPEED = 0x0101

# 键盘控制映射
KEY_MAP = {
    'w': 'forward',      # 前进
    's': 'backward',     # 后退
    'a': 'left',         # 左移（全向轮）
    'd': 'right',        # 右移（全向轮）
    'q': 'rotate_ccw',   # 逆时针旋转
    'e': 'rotate_cw',    # 顺时针旋转
    ' ': 'stop',         # 停止
    '\x03': 'quit',      # Ctrl+C
}


def calculate_crc8(data: bytes) -> int:
    """计算CRC8校验"""
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


def calculate_crc16(data: bytes) -> int:
    """计算CRC16校验 (MODBUS标准)"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def pack_frame(cmd_id: int, data: bytes, seq: int) -> bytes:
    """打包数据帧"""
    # 1. 计算payload长度 (cmd_id 2字节 + data)
    payload_len = 2 + len(data)
    
    # 2. 构建帧头数据 (用于CRC8计算)
    header_data = struct.pack('<HBB', payload_len, seq, 0)  # data_length(2) + seq(1) + padding(1)
    crc8 = calculate_crc8(header_data)
    
    # 3. 构建帧头 (5字节)
    frame_header = struct.pack('<BHB', FRAME_HEADER_SOF, payload_len, seq) + bytes([crc8])
    
    # 4. 构建命令ID (小端序，2字节)
    cmd_id_bytes = struct.pack('<H', cmd_id)
    
    # 5. 构建完整帧 (不含CRC16)
    frame_without_crc16 = frame_header + cmd_id_bytes + data
    
    # 6. 计算整帧CRC16
    crc16 = calculate_crc16(frame_without_crc16)
    crc16_bytes = struct.pack('<H', crc16)
    
    # 7. 返回完整帧
    return frame_without_crc16 + crc16_bytes


class DirectSerialKeyboardControl:
    """直接串口键盘控制类"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200,
                 linear_speed: float = 0.2, angular_speed: float = 0.2):
        self.port = port
        self.baudrate = baudrate
        self.linear_speed = linear_speed
        self.angular_speed = angular_speed
        
        # 串口对象
        self.serial_port: Optional[serial.Serial] = None
        
        # 当前速度状态
        self.pressed_keys = set()
        self.key_last_press_time = {}
        self.key_release_timeout = 0.15  # 按键释放检测超时（秒）
        
        # 序列号 (0-255循环)
        self.tx_seq = 0
        
        # 运行标志
        self.running = True
        
        # 终端设置
        self.settings = None
        
        # 检查stdin是否是终端设备
        if not sys.stdin.isatty():
            print("错误: stdin不是终端设备！")
            print("请从终端直接运行此脚本")
            sys.exit(1)
        
        # 保存终端设置
        try:
            self.settings = termios.tcgetattr(sys.stdin)
        except termios.error as e:
            print(f"错误: 无法获取终端属性: {e}")
            sys.exit(1)
    
    def open_serial(self) -> bool:
        """打开串口"""
        try:
            # 尝试自动检测串口
            ports_to_try = [self.port]
            if self.port == '/dev/ttyUSB0':
                ports_to_try = ['/dev/ttyUSB0', '/dev/ttyUSB1']
            elif self.port == '/dev/ttyUSB1':
                ports_to_try = ['/dev/ttyUSB1', '/dev/ttyUSB0']
            
            for port in ports_to_try:
                try:
                    self.serial_port = serial.Serial(
                        port=port,
                        baudrate=self.baudrate,
                        timeout=0.1,
                        write_timeout=0.1
                    )
                    self.port = port  # 更新为实际使用的端口
                    print(f"✓ 串口已打开: {port} @ {self.baudrate} baud")
                    return True
                except serial.SerialException:
                    continue
            
            print(f"错误: 无法打开串口 {self.port}")
            return False
        except Exception as e:
            print(f"错误: 打开串口失败: {e}")
            return False
    
    def close_serial(self):
        """关闭串口"""
        if self.serial_port and self.serial_port.is_open:
            # 发送停止指令
            self.send_chassis_speed(0.0, 0.0, 0.0)
            time.sleep(0.1)
            self.serial_port.close()
            print("串口已关闭")
    
    def send_chassis_speed(self, vx: float, vy: float, wz: float):
        """发送底盘速度指令"""
        if not self.serial_port or not self.serial_port.is_open:
            return
        
        # 打包数据 (3个float，12字节)
        data = struct.pack('<fff', vx, vy, wz)
        
        # 打包帧
        frame = pack_frame(CMD_CHASSIS_SPEED, data, self.tx_seq)
        
        try:
            # 发送数据
            bytes_written = self.serial_port.write(frame)
            if bytes_written == len(frame):
                # 序列号自增（0-255循环）
                self.tx_seq = (self.tx_seq + 1) % 256
            else:
                print(f"警告: 部分写入 {bytes_written}/{len(frame)} 字节")
        except serial.SerialTimeoutException:
            print("警告: 串口写入超时")
        except Exception as e:
            print(f"错误: 发送数据失败: {e}")
    
    def get_key(self) -> Optional[str]:
        """非阻塞获取键盘输入"""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None
    
    def calculate_speed(self) -> tuple:
        """根据按下的按键计算速度"""
        vx, vy, wz = 0.0, 0.0, 0.0
        
        for key in self.pressed_keys:
            if key not in KEY_MAP:
                continue
            
            action = KEY_MAP[key]
            
            if action == 'forward':
                vx = self.linear_speed
            elif action == 'backward':
                vx = -self.linear_speed
            elif action == 'left':
                vy = self.linear_speed  # 全向轮：左移
            elif action == 'right':
                vy = -self.linear_speed  # 全向轮：右移
            elif action == 'rotate_ccw':
                wz = self.angular_speed
            elif action == 'rotate_cw':
                wz = -self.angular_speed
        
        return vx, vy, wz
    
    def keyboard_listener(self):
        """键盘监听线程"""
        tty.setraw(sys.stdin.fileno())
        
        try:
            while self.running:
                key = self.get_key()
                if key is None:
                    time.sleep(0.01)
                    continue
                
                key_lower = key.lower()
                
                # 处理特殊按键
                if key == '\x03':  # Ctrl+C
                    print("\n收到退出信号")
                    self.running = False
                    break
                
                # 处理按键按下/释放
                if key_lower in KEY_MAP:
                    action = KEY_MAP[key_lower]
                    
                    if action == 'stop':
                        # 空格键：清除所有按键状态并立即发送停止
                        self.pressed_keys.clear()
                        self.send_chassis_speed(0.0, 0.0, 0.0)
                        print('停止')
                    elif action == 'quit':
                        continue  # 已在上面处理
                    else:
                        # 按键事件：记录按下时间
                        current_time = time.time()
                        self.key_last_press_time[key_lower] = current_time
                        
                        # 如果按键不在按下集合中，添加并立即发送
                        if key_lower not in self.pressed_keys:
                            self.pressed_keys.add(key_lower)
                            # 立即发送一次，减少延迟
                            vx, vy, wz = self.calculate_speed()
                            self.send_chassis_speed(vx, vy, wz)
                        # 如果按键已经在按下集合中，可能是重复按下，也立即发送
                        else:
                            vx, vy, wz = self.calculate_speed()
                            self.send_chassis_speed(vx, vy, wz)
        
        except Exception as e:
            print(f"键盘监听错误: {e}")
        finally:
            # 恢复终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
    
    def update_and_send(self):
        """更新速度并发送（定时调用）"""
        if not self.running:
            return
        
        # 检测按键释放（如果按键超过一定时间没有再次按下，认为已释放）
        current_time = time.time()
        keys_to_remove = []
        for key in self.pressed_keys:
            if key in self.key_last_press_time:
                elapsed = current_time - self.key_last_press_time[key]
                if elapsed > self.key_release_timeout:
                    keys_to_remove.append(key)
        
        # 移除已释放的按键
        for key in keys_to_remove:
            self.pressed_keys.discard(key)
            if key in self.key_last_press_time:
                del self.key_last_press_time[key]
        
        # 只有在有按键按下时才发送速度指令
        # 如果没有按键，不发送任何指令（不发送停止指令）
        if self.pressed_keys:
            vx, vy, wz = self.calculate_speed()
            self.send_chassis_speed(vx, vy, wz)
    
    def print_instructions(self):
        """打印使用说明"""
        instructions = """
========================================
直接串口键盘控制（全向轮模式）
========================================
  W/S    : 前进/后退
  A/D    : 左移/右移
  Q/E    : 逆时针/顺时针旋转
  空格键  : 停止
  Ctrl+C : 退出
========================================
串口: {}
波特率: {}
线速度: {} m/s
角速度: {} rad/s
========================================
""".format(self.port, self.baudrate, self.linear_speed, self.angular_speed)
        print(instructions)
    
    def run(self):
        """运行主循环"""
        # 打开串口
        if not self.open_serial():
            return
        
        # 打印使用说明
        self.print_instructions()
        
        # 启动键盘监听线程
        keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        keyboard_thread.start()
        
        # 主循环：定期更新并发送速度指令
        try:
            while self.running:
                self.update_and_send()
                time.sleep(0.02)  # 50Hz
        except KeyboardInterrupt:
            print("\n收到中断信号")
            self.running = False
        finally:
            # 清理
            self.close_serial()
            print("程序已退出")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='直接串口键盘控制程序')
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0',
                       help='串口设备路径 (默认: /dev/ttyUSB0)')
    parser.add_argument('--baudrate', type=int, default=115200,
                       help='波特率 (默认: 115200)')
    parser.add_argument('--linear-speed', type=float, default=0.2,
                       help='线速度 (m/s) (默认: 0.2)')
    parser.add_argument('--angular-speed', type=float, default=0.2,
                       help='角速度 (rad/s) (默认: 0.2)')
    
    args = parser.parse_args()
    
    # 创建并运行控制器
    controller = DirectSerialKeyboardControl(
        port=args.port,
        baudrate=args.baudrate,
        linear_speed=args.linear_speed,
        angular_speed=args.angular_speed
    )
    
    controller.run()


if __name__ == '__main__':
    main()
