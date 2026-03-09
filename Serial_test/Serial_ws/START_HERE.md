# 🚀 简化启动指南

## 问题已解决！

之前的 `ros2 launch` 命令有环境问题，现在改用 `ros2 run` 直接运行节点。

---

## ⚡ 快速启动（推荐）

### 方法1: 使用启动脚本（最简单）

**终端1 - 启动电机控制：**
```bash
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
./start_motor_controller.sh
```

**终端2 - 启动键盘控制：**
```bash
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
./start_keyboard_control.sh
```

---

### 方法2: 手动命令

**终端1 - 启动电机控制：**
```bash
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
source install/setup.bash

# 给串口权限
sudo chmod 666 /dev/ttyUSB0

# 启动节点
ros2 run my_package_py motor_controller \
  --ros-args -p port:=/dev/ttyUSB0 -p baudrate:=115200
```

**预期输出：**
```
[INFO] [motor_controller]: Successfully connected to /dev/ttyUSB0 at 115200 baud
[INFO] [motor_controller]: Started serial receive thread
[INFO] [motor_controller]: Motor Controller Node initialized
```

**终端2 - 启动键盘控制：**
```bash
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
source install/setup.bash
ros2 run my_package_py keyboard_control
```

---

## ⌨️ 键盘控制说明

启动后你会看到：
```
==================================================
      键盘电机控制 - Keyboard Motor Control
==================================================

M3508电机控制:
  W - 增加档位
  S - 减少档位
  X - 紧急停止

M2006电机控制:
  A - 增加档位
  D - 减少档位
  C - 紧急停止

其他:
  Q - 退出
  SPACE - 全部停止
==================================================
```

**操作示例：**
1. 按 `W` → M3508 低速运转（终端1会显示: `Sent control: Motor=3508, Gear=LOW`）
2. 再按 `W` → M3508 中速运转
3. 再按 `W` → M3508 高速运转
4. 按 `S` → M3508 降回中速
5. 按 `A` → M2006 低速运转
6. 按空格 → 全部停止
7. 按 `Q` → 退出程序

---

## 🔍 监控数据（可选）

**终端3 - 监控速度命令：**
```bash
source install/setup.bash
ros2 topic echo /cmd_vel
```

会显示当前发送的速度值：
```yaml
linear:
  x: 0.3  # M3508速度
angular:
  z: 0.6  # M2006速度
```

---

## ❗ 常见问题

### 1. 串口权限被拒绝
```bash
sudo chmod 666 /dev/ttyUSB0
```

### 2. 找不到串口设备
```bash
# 查看所有串口
ls /dev/ttyUSB* /dev/ttyACM*

# 如果是 /dev/ttyACM0，修改命令：
ros2 run my_package_py motor_controller \
  --ros-args -p port:=/dev/ttyACM0 -p baudrate:=115200
```

### 3. 节点启动失败
```bash
# 重新编译
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
colcon build
source install/setup.bash
```

---

## 📊 数据包验证

在终端1（电机控制节点）的日志中，你应该看到：
```
[INFO]: Sent control: Motor=3508, Gear=LOW
[DEBUG]: Raw packet: 55 AA 01 01 F1 98 0D
```

这个数据包会通过串口发送到STM32：
- `55 AA` - 帧头
- `01` - M3508电机
- `01` - 低速档位
- `F1 98` - CRC16校验
- `0D` - 帧尾

---

## ✅ 完整流程

1. **连接硬件** - USB线连接STM32
2. **给权限** - `sudo chmod 666 /dev/ttyUSB0`
3. **启动控制节点** - `./start_motor_controller.sh`
4. **启动键盘控制** - `./start_keyboard_control.sh`（新终端）
5. **控制电机** - 按 W/S/A/D 键
6. **停止** - 按 Q 退出，Ctrl+C 停止节点

---

## 🎯 下一步

- ✅ 节点已能正常运行
- ✅ 协议与STM32完全对齐
- ✅ 键盘控制已就绪
- 🔲 连接实际硬件测试
- 🔲 验证电机响应

**现在可以开始实际测试了！** 🎉
