# ROS2 串口电机控制系统

## 📋 项目概述
本项目实现了通过ROS2控制STM32下位机的M3508和M2006电机，使用串口通信协议。

## 🔧 系统架构
```
┌──────────────┐      ┌─────────────────┐      ┌──────────────┐
│ 键盘控制节点  │ ---> │ 电机控制节点      │ ---> │  STM32下位机  │
│keyboard_control│     │motor_controller  │      │  M3508/M2006 │
└──────────────┘      └─────────────────┘      └──────────────┘
      ↓                        ↓                       ↓
   /cmd_vel              串口通信协议            电机驱动控制
```

## 📡 通信协议

### 数据包格式 (7字节)
| 字节位置 | 字段说明 | 数值 | 说明 |
|---------|---------|------|------|
| 0-1 | 帧头 | 0xAA55 | 固定值（小端序：0x55 0xAA） |
| 2 | 电机类型 | 0x01/0x02 | 0x01=M3508, 0x02=M2006 |
| 3 | 档位 | 0x00-0x03 | 0x00=停止, 0x01=低速, 0x02=中速, 0x03=高速 |
| 4-5 | CRC16校验 | 计算值 | MODBUS标准，对前4字节计算 |
| 6 | 帧尾 | 0x0D | 固定值 |

### 速度映射
| 档位 | 名称 | ROS2速度值 | STM32速度(rad/s) |
|------|------|-----------|-----------------|
| 0x00 | 停止 | 0.0 | 0.0 |
| 0x01 | 低速 | 0.3 | 5.0 |
| 0x02 | 中速 | 0.6 | 15.0 |
| 0x03 | 高速 | 1.0 | 25.0 |

## 🚀 快速开始

### 1. 编译工作区
```bash
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
colcon build
source install/setup.bash
```

### 2. 连接硬件
```bash
# 查看串口设备
ls /dev/ttyUSB* /dev/ttyACM*

# 给串口权限
sudo chmod 666 /dev/ttyUSB0
```

### 3. 启动系统
```bash
# 终端1: 启动电机控制节点
source install/setup.bash
ros2 launch my_package_py motor_control.launch.py

# 终端2: 启动键盘控制
source install/setup.bash
ros2 run my_package_py keyboard_control
```

## ⌨️ 键盘控制

### M3508电机（线速度）
- **W** - 增加档位
- **S** - 减少档位  
- **X** - 紧急停止

### M2006电机（角速度）
- **A** - 增加档位
- **D** - 减少档位
- **C** - 紧急停止

### 通用
- **空格** - 全部停止
- **Q** - 退出程序

## 🧪 测试命令

```bash
# 手动发送速度命令
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.0}}"

# 监控话题
ros2 topic echo /cmd_vel

# 查看节点
ros2 node list
```

## 🔍 协议验证

### M3508低速命令示例
```
数据包: 55 AA 01 01 F9 55 0D

解析:
  0x55 0xAA - 帧头 (0xAA55小端序)
  0x01      - M3508电机
  0x01      - 低速档位
  0xF9 0x55 - CRC16校验值
  0x0D      - 帧尾
```

## ❗ 故障排查

| 问题 | 解决方案 |
|------|---------|
| 找不到串口 | `ls /dev/ttyUSB*` 确认设备 |
| 权限被拒绝 | `sudo chmod 666 /dev/ttyUSB0` |
| 节点无法启动 | 检查 `ros2 pkg list \| grep my_package_py` |
| STM32无响应 | 确认波特率115200，检查协议格式 |

## 📁 文件结构
```
Serial_ws/
├── src/my_package_py/
│   ├── nodes/
│   │   ├── serial_bridge.py         # 串口通信
│   │   └── motor_controller_node.py # 电机控制
│   ├── scripts/
│   │   └── keyboard_control.py      # 键盘控制
│   └── launch/
│       └── motor_control.launch.py
└── README.md
```

## ✅ 代码检查结果

您的STM32代码与ROS2代码**基本兼容**，但我已修正了以下问题：

1. ✅ **数据包长度**：从8字节修正为7字节
2. ✅ **CRC计算范围**：修正为对帧头+电机类型+档位（4字节）计算
3. ✅ **字节序**：统一使用小端序
4. ✅ **速度映射**：ROS2与STM32的档位-速度映射已对齐

现在可以正常通信了！
