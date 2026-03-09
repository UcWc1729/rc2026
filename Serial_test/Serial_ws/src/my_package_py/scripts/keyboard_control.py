#!/usr/bin/env python3
"""
键盘控制电机 - 直接通过键盘按键控制M3508和M2006电机
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import termios
import tty
import select

class KeyboardController(Node):
    def __init__(self):
        super().__init__('keyboard_controller')
        
        # 创建cmd_vel发布者
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # 电机控制状态
        self.motor_3508_gear = 0  # 0=停止, 1=低速, 2=中速, 3=高速
        self.motor_2006_gear = 0
        
        # 获取终端设置
        self.settings = termios.tcgetattr(sys.stdin)
        
        self.print_instructions()
    
    def print_instructions(self):
        """打印控制说明"""
        print("\n" + "="*50)
        print("      键盘电机控制 - Keyboard Motor Control")
        print("="*50)
        print("\nM3508电机控制 (通过linear.x):")
        print("  W - 增加档位 (停止->低速->中速->高速)")
        print("  S - 减少档位")
        print("  X - 紧急停止")
        print("\nM2006电机控制 (通过angular.z):")
        print("  A - 增加档位 (停止->低速->中速->高速)")
        print("  D - 减少档位")
        print("  C - 紧急停止")
        print("\n其他:")
        print("  Q - 退出程序")
        print("  SPACE - 所有电机停止")
        print("="*50)
        print(f"\n当前状态: 3508={self.get_gear_name(self.motor_3508_gear)}, "
              f"2006={self.get_gear_name(self.motor_2006_gear)}")
    
    def get_gear_name(self, gear):
        """获取档位名称"""
        names = ["停止", "低速", "中速", "高速"]
        return names[gear] if 0 <= gear < len(names) else "未知"
    
    def get_speed_value(self, gear):
        """将档位转换为速度值"""
        # 档位对应的速度映射
        speed_map = {
            0: 0.0,    # 停止
            1: 0.3,    # 低速 (对应SPEED_LOW = 5 rad/s)
            2: 0.6,    # 中速 (对应SPEED_MID = 15 rad/s)
            3: 1.0     # 高速 (对应SPEED_HIGH = 25 rad/s)
        }
        return speed_map.get(gear, 0.0)
    
    def publish_velocity(self):
        """发布速度命令"""
        msg = Twist()
        msg.linear.x = self.get_speed_value(self.motor_3508_gear)
        msg.angular.z = self.get_speed_value(self.motor_2006_gear)
        self.cmd_vel_pub.publish(msg)
        
        # 显示当前状态
        print(f"\r当前状态: 3508={self.get_gear_name(self.motor_3508_gear)} ({msg.linear.x:.1f}), "
              f"2006={self.get_gear_name(self.motor_2006_gear)} ({msg.angular.z:.1f})   ", 
              end='', flush=True)
    
    def get_key(self):
        """获取键盘按键(非阻塞)"""
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key
    
    def run(self):
        """运行主循环"""
        try:
            while rclpy.ok():
                key = self.get_key()
                
                if key == '':
                    continue
                
                key_lower = key.lower()
                
                # 退出
                if key_lower == 'q':
                    print("\n\n退出程序...")
                    break
                
                # M3508控制 (W/S/X)
                elif key_lower == 'w':
                    if self.motor_3508_gear < 3:
                        self.motor_3508_gear += 1
                        self.get_logger().info(f"3508档位增加到: {self.get_gear_name(self.motor_3508_gear)}")
                
                elif key_lower == 's':
                    if self.motor_3508_gear > 0:
                        self.motor_3508_gear -= 1
                        self.get_logger().info(f"3508档位降低到: {self.get_gear_name(self.motor_3508_gear)}")
                
                elif key_lower == 'x':
                    self.motor_3508_gear = 0
                    self.get_logger().info("3508紧急停止!")
                
                # M2006控制 (A/D/C)
                elif key_lower == 'a':
                    if self.motor_2006_gear < 3:
                        self.motor_2006_gear += 1
                        self.get_logger().info(f"2006档位增加到: {self.get_gear_name(self.motor_2006_gear)}")
                
                elif key_lower == 'd':
                    if self.motor_2006_gear > 0:
                        self.motor_2006_gear -= 1
                        self.get_logger().info(f"2006档位降低到: {self.get_gear_name(self.motor_2006_gear)}")
                
                elif key_lower == 'c':
                    self.motor_2006_gear = 0
                    self.get_logger().info("2006紧急停止!")
                
                # 全部停止
                elif key == ' ':
                    self.motor_3508_gear = 0
                    self.motor_2006_gear = 0
                    self.get_logger().info("所有电机停止!")
                
                # 发布速度命令
                self.publish_velocity()
                
        except Exception as e:
            self.get_logger().error(f"错误: {e}")
        finally:
            # 恢复终端设置
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
            # 停止所有电机
            self.motor_3508_gear = 0
            self.motor_2006_gear = 0
            self.publish_velocity()
            print("\n")

def main(args=None):
    rclpy.init(args=args)
    
    controller = KeyboardController()
    controller.run()
    
    controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
