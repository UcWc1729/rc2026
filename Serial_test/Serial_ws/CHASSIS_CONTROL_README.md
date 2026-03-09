# 底盘速度控制使用说明

## 功能说明

实现了基于通用上下位机通信协议的底盘速度控制功能，可以通过串口发送速度命令到下位机（STM32）。

## 文件说明

1. **protocol_handler.py** - 通信协议处理类
   - 实现帧打包和解析
   - CRC8/CRC16校验
   - 支持底盘速度、急停、心跳等命令

2. **chassis_speed_controller.py** - ROS2节点
   - 订阅`/cmd_vel`话题接收速度命令
   - 通过串口发送到下位机
   - 自动发送心跳包
   - 启动时自动发送测试命令（Vx=0.1, Vy=0, Wz=0）

3. **test_chassis_speed.py** - 独立测试脚本
   - 不依赖ROS2直接测试串口通信
   - 发送固定的速度命令
   - 显示详细的帧信息

## 使用方法

### 方法1：使用测试脚本（推荐新手）

直接运行测试脚本，无需启动ROS2：

```bash
cd /home/changes/2026ROBOCON/Task/Serial_test/Serial_ws
python3 test_chassis_speed.py
```

**优点**：
- 无需ROS2环境
- 输出详细的调试信息
- 快速验证串口通信

### 方法2：使用ROS2节点

#### 2.1 启动节点

```bash
cd /home/changes/2026ROBOCON/Task/Serial_test/Serial_ws
./start_chassis_controller.sh
```

或者手动启动：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run my_package_py chassis_controller
```

**节点启动时会自动发送测试命令：Vx=0.1, Vy=0, Wz=0**

#### 2.2 通过话题发送速度命令

在另一个终端：

```bash
# 发送前进速度
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# 发送旋转速度
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"

# 发送全向移动（Vx=0.1, Vy=0.2, Wz=0.3）
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1, y: 0.2, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.3}}"
```

## 配置参数

可以通过ROS2参数修改配置：

```bash
ros2 run my_package_py chassis_controller \
    --ros-args \
    -p serial_port:=/dev/ttyUSB0 \     # 串口设备
    -p baudrate:=115200 \              # 波特率
    -p cmd_vel_topic:=cmd_vel \        # 订阅话题
    -p heartbeat_rate:=10.0            # 心跳频率(Hz)
```

## 协议说明

### 帧格式

```
+------+--------+-----+------+--------+------+--------+
| SOF  | LEN(2) | SEQ | CRC8 | CMD_ID | DATA | CRC16  |
| 1B   | 2B     | 1B  | 1B   | 2B     | 12B  | 2B     |
+------+--------+-----+------+--------+------+--------+
```

### 底盘速度命令（CMD_ID: 0x0101）

**数据格式**：
- vx: float (4字节) - X方向速度 (m/s)
- vy: float (4字节) - Y方向速度 (m/s)  
- wz: float (4字节) - 旋转角速度 (rad/s)

**示例帧**（Vx=0.1, Vy=0, Wz=0）：

```
A5 0E00 00 XX 0101 CDCCCC3D00000000000000 XXXX
│  │    │  │  │    │                       │
│  │    │  │  │    └─ 数据: 0.1f, 0.0f, 0.0f (小端序)
│  │    │  │  └────── 命令ID: 0x0101
│  │    │  └───────── CRC8校验
│  │    └──────────── 序列号
│  └───────────────── 数据长度: 14字节 (2+12)
└──────────────────── 帧头: 0xA5
```

## 调试

### 查看串口设备

```bash
ls /dev/tty*
# 或
dmesg | grep tty
```

### 添加串口权限

```bash
sudo chmod 666 /dev/ttyUSB0
# 或永久添加到dialout组
sudo usermod -aG dialout $USER
```

### 查看ROS2话题

```bash
# 查看所有话题
ros2 topic list

# 查看cmd_vel话题
ros2 topic echo /cmd_vel

# 查看话题频率
ros2 topic hz /cmd_vel
```

### 查看节点日志

```bash
ros2 run my_package_py chassis_controller --ros-args --log-level debug
```

## 测试输出示例

### 测试脚本输出

```
======================================================================
底盘速度控制测试
======================================================================
串口: /dev/ttyUSB0
波特率: 115200
命令: Vx=0.1 m/s, Vy=0 m/s, Wz=0 rad/s
======================================================================

📦 生成的数据帧:
  总长度: 21 字节
  十六进制: a50e000069010100cdcccc3d000000000000000062c0
  详细结构:
    - SOF (帧头):        0xA5
    - 数据长度:          14 字节
    - 序列号:            0
    - CRC8:              0x69
    - 命令ID:            0x0101
    - 数据段 (12字节):   cdcccc3d00000000000000
    - CRC16:             0xC062

🔌 连接串口 /dev/ttyUSB0...
✓ 串口连接成功

📤 发送数据...
✓ 成功发送 21 字节

======================================================================
测试完成
======================================================================
```

### ROS2节点输出

```
[INFO] [chassis_speed_controller]: Chassis Speed Controller initialized
[INFO] [chassis_speed_controller]: Serial Port: /dev/ttyUSB0 @ 115200 baud
[INFO] [chassis_speed_controller]: Subscribing to: cmd_vel
[INFO] [chassis_speed_controller]: ✓ Serial port connected: /dev/ttyUSB0
[INFO] [chassis_speed_controller]: ============================================================
[INFO] [chassis_speed_controller]: Sending TEST command: Vx=0.1, Vy=0, Wz=0
[INFO] [chassis_speed_controller]: ============================================================
[INFO] [chassis_speed_controller]: Sending speed command: vx=0.100, vy=0.000, wz=0.000 [Frame: 21 bytes]
[INFO] [chassis_speed_controller]: ✓ Test command sent successfully
```

## 故障排除

### 问题1：串口连接失败

**解决方法**：
1. 检查串口是否存在：`ls /dev/ttyUSB*`
2. 检查权限：`sudo chmod 666 /dev/ttyUSB0`
3. 检查是否被占用：`lsof /dev/ttyUSB0`

### 问题2：没有收到数据

**检查项**：
1. 波特率是否匹配（115200）
2. 下位机是否正常运行
3. TX/RX线是否接反
4. 使用逻辑分析仪查看串口波形

### 问题3：CRC校验错误

**原因**：
- 数据传输过程中损坏
- 波特率不匹配
- 接线质量问题

## 扩展功能

### 添加其他命令

在`protocol_handler.py`中添加新的打包函数：

```python
def pack_your_command(self, param1, param2) -> bytes:
    data = struct.pack('<ff', param1, param2)
    return self.pack_frame(YOUR_CMD_ID, data)
```

### 接收下位机反馈

在`chassis_speed_controller.py`中添加接收线程：

```python
def receive_thread_func(self):
    while self.running:
        if self.serial_conn.in_waiting > 0:
            data = self.serial_conn.read(self.serial_conn.in_waiting)
            # 解析数据
            success, cmd_id, data, seq = self.protocol.parse_frame(data)
            if success:
                # 处理反馈
                pass
```

## 参考资料

- 通信协议文档：`通用上下位机通信协议设计文档.md`
- C语言实现：`protocol_chassis.c` 和 `protocol_chassis.h`
- ROS2官方文档：https://docs.ros.org/en/humble/
