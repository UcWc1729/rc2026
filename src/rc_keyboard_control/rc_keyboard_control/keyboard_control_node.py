#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
键盘控制节点
通过键盘控制机器人底盘移动
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import select
import termios
import tty
import threading
import time

# 键盘控制映射
KEY_MAP = {
    'w': 'forward',      # 前进
    's': 'backward',      # 后退
    'a': 'left',          # 左移（全向轮）或左转
    'd': 'right',         # 右移（全向轮）或右转
    'q': 'rotate_ccw',    # 逆时针旋转
    'e': 'rotate_cw',     # 顺时针旋转
    ' ': 'stop',          # 停止
    '\x03': 'quit',       # Ctrl+C
}

class KeyboardControlNode(Node):
    """键盘控制节点"""
    
    def __init__(self):
        super().__init__('keyboard_control_node')
        
        # 声明参数
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('linear_speed', 0.05)      # 线速度 (m/s)
        self.declare_parameter('angular_speed', 0.05)     # 角速度 (rad/s)
        self.declare_parameter('publish_rate', 50.0)     # 发布频率 (Hz) - 提高频率降低延迟
        
        # 获取参数
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').get_parameter_value().string_value
        self.linear_speed = self.get_parameter('linear_speed').get_parameter_value().double_value
        self.angular_speed = self.get_parameter('angular_speed').get_parameter_value().double_value
        publish_rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        
        # 创建发布者
        self.cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        
        # 当前速度状态
        self.current_twist = Twist()
        self.pressed_keys = set()  # 跟踪按下的按键
        self.key_last_press_time = {}  # 记录每个按键的最后按下时间（用于检测释放）
        self.key_release_timeout = 0.15  # 按键释放检测超时（秒）
        
        # 创建定时器，定期发布速度指令和更新速度
        timer_period = 1.0 / publish_rate
        self.timer = self.create_timer(timer_period, self.update_and_publish)
        
        # 检查stdin是否是终端设备
        if not sys.stdin.isatty():
            self.get_logger().error(
                'stdin不是终端设备！\n'
                '键盘控制节点必须从终端直接运行，不能通过launch文件启动。\n'
                '请使用: ros2 run rc_keyboard_control keyboard_control_node'
            )
            raise RuntimeError('stdin不是终端设备，请从终端直接运行节点')
        
        # 保存终端设置
        try:
            self.settings = termios.tcgetattr(sys.stdin)
        except termios.error as e:
            self.get_logger().error(f'无法获取终端属性: {e}')
            self.get_logger().error('请确保从终端直接运行节点，而不是通过launch文件')
            raise
        
        # 启动键盘监听线程
        self.running = True
        self.keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        self.keyboard_thread.start()
        
        self.get_logger().info('键盘控制节点已启动')
        self.print_instructions()
    
    def print_instructions(self):
        """打印使用说明"""
        instructions = """
========================================
键盘控制说明（全向轮模式）:
========================================
  W/S    : 前进/后退
  A/D    : 左移/右移
  Q/E    : 逆时针/顺时针旋转
  空格键  : 停止
  Ctrl+C : 退出
========================================
"""
        print(instructions)
    
    def get_key(self):
        """非阻塞获取键盘输入"""
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
        return None
    
    def keyboard_listener(self):
        """键盘监听线程"""
        tty.setraw(sys.stdin.fileno())
        
        try:
            while self.running:
                key = self.get_key()
                if key is None:
                    continue
                
                key_lower = key.lower()
                
                # 处理特殊按键
                if key == '\x03':  # Ctrl+C
                    self.get_logger().info('收到退出信号')
                    self.running = False
                    rclpy.shutdown()
                    break
                
                # 处理按键按下/释放
                if key_lower in KEY_MAP:
                    action = KEY_MAP[key_lower]
                    
                    if action == 'stop':
                        # 空格键：清除所有按键状态并立即发布停止
                        self.pressed_keys.clear()
                        stop_twist = Twist()
                        self.cmd_vel_pub.publish(stop_twist)
                        self.get_logger().info('停止')
                    elif action == 'quit':
                        continue  # 已在上面处理
                    else:
                        # 按键事件：记录按下时间
                        current_time = time.time()
                        self.key_last_press_time[key_lower] = current_time
                        
                        # 如果按键不在按下集合中，添加并立即发布
                        if key_lower not in self.pressed_keys:
                            self.pressed_keys.add(key_lower)
                            # 立即发布一次，减少延迟
                            self.publish_immediate()
                        # 如果按键已经在按下集合中，可能是重复按下，也立即发布
                        else:
                            self.publish_immediate()
        
        except Exception as e:
            self.get_logger().error(f'键盘监听错误: {e}')
        finally:
            # 恢复终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
    
    def calculate_twist(self):
        """根据按下的按键计算速度"""
        twist = Twist()
        
        # 根据按下的按键更新速度
        for key in self.pressed_keys:
            if key not in KEY_MAP:
                continue
            
            action = KEY_MAP[key]
            
            if action == 'forward':
                twist.linear.x = self.linear_speed
            elif action == 'backward':
                twist.linear.x = -self.linear_speed
            elif action == 'left':
                twist.linear.y = self.linear_speed  # 全向轮：左移
            elif action == 'right':
                twist.linear.y = -self.linear_speed  # 全向轮：右移
            elif action == 'rotate_ccw':
                twist.angular.z = self.angular_speed
            elif action == 'rotate_cw':
                twist.angular.z = -self.angular_speed
        
        return twist
    
    def publish_immediate(self):
        """立即发布当前速度（用于按键按下时减少延迟）"""
        if not self.running:
            return
        twist = self.calculate_twist()
        self.cmd_vel_pub.publish(twist)
    
    def update_and_publish(self):
        """根据按下的按键更新速度并发布（定时器调用）"""
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
        
        # 只有在有按键按下时才发布速度指令
        # 如果没有按键，不发布任何消息（不发送停止指令）
        if self.pressed_keys:
            twist = self.calculate_twist()
            self.cmd_vel_pub.publish(twist)
    
    def destroy_node(self):
        """节点销毁时停止机器人"""
        self.running = False
        # 发送停止指令
        stop_twist = Twist()
        self.cmd_vel_pub.publish(stop_twist)
        # 恢复终端设置
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    
    node = KeyboardControlNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
