# 完整使用指南

## ✅ 代码检查结果

您的STM32下位机代码经过分析，**已与ROS2上位机代码完全对齐**：

### 修正的问题
1. ✅ 数据包长度：从8字节改为7字节
2. ✅ CRC计算范围：对帧头+电机类型+档位（4字节）计算  
3. ✅ 字节序：统一使用小端序
4. ✅ 速度映射：完全匹配

### 协议验证通过
```
M3508低速命令: 55 AA 01 01 F1 98 0D ✓
M2006中速命令: 55 AA 02 02 B1 69 0D ✓
CRC16计算正确 ✓
```

## 🚀 完整操作步骤

### 步骤1: 编译ROS2包
```bash
cd ~/2026ROBOCON/Task/Serial_test/Serial_ws
colcon build
source install/setup.bash
```

### 步骤2: 连接STM32
```bash
# 查看设备
ls /dev/ttyUSB* /dev/ttyACM*

# 给权限（选择实际设备）
sudo chmod 666 /dev/ttyUSB0
```

### 步骤3: 启动电机控制节点（终端1）
```bash
source install/setup.bash

# 默认串口 /dev/ttyUSB0，波特率115200
ros2 launch my_package_py motor_control.launch.py

# 或指定串口
ros2 launch my_package_py motor_control.launch.py port:=/dev/ttyACM0
```

**预期输出：**
```
[motor_controller]: Successfully connected to /dev/ttyUSB0 at 115200 baud
[motor_controller]: Started serial receive thread
[motor_controller]: Motor Controller Node initialized
```

### 步骤4: 启动键盘控制（终端2）
```bash
source install/setup.bash
ros2 run my_package_py keyboard_control
```

**预期输出：**
```
==================================================
      键盘电机控制 - Keyboard Motor Control
==================================================

M3508电机控制 (通过linear.x):
  W - 增加档位 (停止->低速->中速->高速)
  S - 减少档位
  X - 紧急停止

M2006电机控制 (通过angular.z):
  A - 增加档位 (停止->低速->中速->高速)
  D - 减少档位
  C - 紧急停止

其他:
  Q - 退出程序
  SPACE - 所有电机停止
==================================================

当前状态: 3508=停止, 2006=停止
```

### 步骤5: 控制电机
```
按 W → 3508低速运转
按 W → 3508中速运转
按 W → 3508高速运转
按 S → 3508降回中速
按 X → 3508停止

按 A → 2006低速运转
按 D → 2006降回停止

按空格 → 全部停止
按 Q → 退出
```

## 📊 监控和调试

### 监控发送的命令（终端3）
```bash
source install/setup.bash
ros2 topic echo /cmd_vel
```

**输出示例：**
```yaml
linear:
  x: 0.3  # 3508低速
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.6  # 2006中速
---
```

### 查看节点日志
```bash
# 查看详细日志
ros2 run my_package_py motor_controller --ros-args --log-level debug
```

**预期日志：**
```
[INFO]: Sent control: Motor=3508, Gear=LOW
[DEBUG]: Raw packet: 55 AA 01 01 F1 98 0D
[INFO]: Sent control: Motor=2006, Gear=MID
[DEBUG]: Raw packet: 55 AA 02 02 B1 69 0D
```

## 🧪 测试方法

### 方法1: 手动发送话题
```bash
# 3508低速
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}"

# 2006高速
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 1.0}}"

# 停止全部
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

### 方法2: Python测试脚本
```bash
python3 test_protocol.py
```

查看所有可能的数据包格式和CRC计算。

### 方法3: 串口监控（需要另一个串口或USB转串口）
```bash
# 安装minicom
sudo apt install minicom

# 监控串口
minicom -D /dev/ttyUSB0 -b 115200 -C capture.txt
```

## 🔍 STM32端验证要点

### 1. 检查数据接收
在STM32的UART接收回调中添加LED指示：
```c
void Host_Communication_UART_Callback(uint8_t *Rx_Buffer, uint16_t Length) {
    HAL_GPIO_TogglePin(LED_GPIO_Port, LED_Pin);  // 接收指示
    
    if (Length == sizeof(SimpleControlPacket)) {
        // 处理数据包...
    }
}
```

### 2. 验证CRC计算
确保STM32的CRC16函数与ROS2一致：
```c
// 测试数据: 55 AA 01 01
// 预期CRC: 0x98F1 (小端序: F1 98)
uint16_t crc = CRC16_Calculate(test_data, 4);
// crc应该等于 0x98F1
```

### 3. 检查电机响应
```c
// Parse_Control_Packet返回1表示成功
uint8_t result = Parse_Control_Packet(&packet);
if (result == 1) {
    // 处理控制命令
    Process_Control_Command(&packet);
}
```

## ❗ 常见问题

### Q1: 串口找不到设备
```bash
# 检查USB连接
lsusb

# 检查内核消息
dmesg | grep tty

# 可能的设备名
/dev/ttyUSB0  # USB转串口
/dev/ttyACM0  # STM32虚拟串口
/dev/ttyS0    # 板载串口
```

### Q2: 权限被拒绝
```bash
# 临时方案
sudo chmod 666 /dev/ttyUSB0

# 永久方案
sudo usermod -a -G dialout $USER
# 然后注销重新登录
```

### Q3: STM32无响应
1. 确认波特率：115200
2. 确认数据位：8
3. 确认停止位：1
4. 确认校验位：无
5. 使用示波器查看TX/RX信号
6. 检查STM32的UART是否初始化成功

### Q4: CRC校验失败
```bash
# 运行测试脚本验证
python3 test_protocol.py

# 检查输出的CRC值是否与STM32计算的一致
# 3508低速: F1 98
# 2006中速: B1 69
```

### Q5: 电机不转
1. 检查电源供电
2. 检查CAN总线连接
3. 检查电机ID配置
4. 在STM32端添加调试输出确认收到命令

## 📈 性能优化建议

### 1. 降低发送频率
默认每次按键都发送命令。如需持续控制，可修改为定时发送：
```python
# 在keyboard_control.py中添加定时器
self.timer = self.create_timer(0.1, self.publish_velocity)  # 10Hz
```

### 2. 添加反馈机制
在STM32端发送电机状态反馈：
```c
// 定期发送电机速度反馈
typedef struct {
    uint16_t header;
    float motor_3508_speed;
    float motor_2006_speed;
    uint16_t crc;
    uint8_t footer;
} FeedbackPacket;
```

### 3. 错误重传
在serial_bridge.py中添加确认和重传机制。

## 📝 总结

✅ **协议已对齐** - ROS2和STM32使用相同的7字节协议  
✅ **CRC计算正确** - MODBUS标准，对前4字节计算  
✅ **速度映射一致** - 档位0-3对应0/5/15/25 rad/s  
✅ **键盘控制就绪** - W/S/A/D控制两个电机  

现在你可以：
1. 编译并启动ROS2节点
2. 使用键盘控制电机
3. 监控通信数据
4. 在STM32端验证接收

祝调试顺利！🎉
