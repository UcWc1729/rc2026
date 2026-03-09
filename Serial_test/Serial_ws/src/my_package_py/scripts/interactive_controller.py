#!/usr/bin/env python3
"""
ROS2交互式电机控制脚本
"""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
import sys

class InteractiveController(Node):
    def __init__(self):
        super().__init__('interactive_controller')
        
        # 创建服务客户端
        self.control_3508_client = self.create_client(Trigger, '/motor_3508_control')
        self.control_2006_client = self.create_client(Trigger, '/motor_2006_control')
        
        # 等待服务可用
        while not self.control_3508_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('3508 control service not available, waiting...')
        while not self.control_2006_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('2006 control service not available, waiting...')
        
        print("Interactive Motor Controller")
        print("Commands:")
        print("  1 - Control 3508 Motor")
        print("  2 - Control 2006 Motor") 
        print("  q - Quit")
        print("-" * 40)
    
    def control_3508(self):
        """控制3508电机"""
        request = Trigger.Request()
        future = self.control_3508_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        return future.result()
    
    def control_2006(self):
        """控制2006电机"""
        request = Trigger.Request()
        future = self.control_2006_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        return future.result()
    
    def run(self):
        while rclpy.ok():
            try:
                cmd = input("Enter command: ").strip().lower()
                
                if cmd == 'q':
                    break
                elif cmd == '1':
                    response = self.control_3508()
                    print(f"3508: {response.message}")
                elif cmd == '2':
                    response = self.control_2006()
                    print(f"2006: {response.message}")
                else:
                    print("Invalid command. Use 1, 2, or q.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

def main(args=None):
    rclpy.init(args=args)
    
    controller = InteractiveController()
    controller.run()
    
    controller.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()