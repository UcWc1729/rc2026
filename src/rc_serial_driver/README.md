# rc_serial_driver

串口驱动包，用于与下位机进行通信，将ROS2的速度指令（`/cmd_vel`）通过串口发送给下位机。

## 功能

- 订阅 `/cmd_vel` 话题（`geometry_msgs/Twist`）
- 将速度指令转换为串口协议格式
- 通过串口发送给下位机
- 支持超时检测，超时后自动发送停止指令

## 串口协议格式

本驱动实现了**通用上下位机通信协议 v1.0**，协议格式如下：

### 完整帧结构

```
+------+--------+-----+------+--------+------+--------+
| SOF  | LEN(2) | SEQ | CRC8 | CMD_ID | DATA | CRC16  |
| 1B   | 2B     | 1B  | 1B   | 2B     | 0-64B| 2B     |
+------+--------+-----+------+--------+------+--------+
```

- **SOF**: 起始标志，固定为 `0xA5`
- **LEN**: 数据段长度（CMD_ID + DATA）
- **SEQ**: 包序列号（0-255循环）
- **CRC8**: 帧头校验（对LEN+SEQ共4字节计算）
- **CMD_ID**: 命令ID（小端序）
- **DATA**: 数据段（0-64字节）
- **CRC16**: 整帧校验（MODBUS标准）

### 底盘速度控制命令 (CMD_CHASSIS_SPEED = 0x0101)

数据格式：`float vx, float vy, float wz`（各4字节，共12字节）

- **vx**: 前进速度 (m/s)
- **vy**: 横向速度 (m/s)
- **wz**: 旋转角速度 (rad/s)

### 校验算法

- **CRC8**: 多项式 0x31，初始值 0xFF
- **CRC16**: 多项式 0xA001 (MODBUS)，初始值 0xFFFF

详细协议说明请参考项目根目录的 `通用上下位机通信协议设计文档.md`

## 使用方法

### 1. 编译

```bash
cd ~/ROBOCON2026/lidar_test/CSU-RM-Sentry
colcon build --packages-select rc_serial_driver
source install/setup.bash
```

### 2. 直接启动

```bash
ros2 launch rc_serial_driver serial_driver.launch.py
```

### 3. 带参数启动

```bash
ros2 launch rc_serial_driver serial_driver.launch.py \
    port_name:=/dev/ttyUSB0 \
    baudrate:=115200 \
    cmd_vel_topic:=/cmd_vel \
    max_linear_vel:=1.0 \
    max_angular_vel:=1.0 \
    timeout:=0.1
```

### 4. 使用配置文件

```bash
ros2 run rc_serial_driver serial_driver_node \
    --ros-args \
    --params-file src/rc_serial_driver/config/serial_driver_params.yaml
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `port_name` | string | `/dev/ttyUSB0` | 串口设备路径 |
| `baudrate` | int | `115200` | 波特率（下位机固定为115200） |
| `cmd_vel_topic` | string | `/cmd_vel` | 速度指令话题名称 |
| `max_linear_vel` | double | `1.0` | 最大线速度 (m/s) |
| `max_angular_vel` | double | `1.0` | 最大角速度 (rad/s) |
| `timeout` | double | `0.1` | 超时时间 (秒)，超过此时间未收到指令则发送停止指令 |

## 权限设置

确保当前用户有权限访问串口设备：

```bash
# 查看串口设备
ls -l /dev/ttyUSB*

# 添加用户到dialout组（需要重新登录）
sudo usermod -a -G dialout $USER

# 或者使用udev规则设置权限
sudo chmod 666 /dev/ttyUSB0
```

## 测试

### 1. 测试串口连接

```bash
# 查看串口是否被识别
dmesg | grep tty

# 测试串口读写（需要另一个终端）
cat /dev/ttyUSB0  # 读取
echo "test" > /dev/ttyUSB0  # 写入
```

### 2. 测试速度指令发布

```bash
# 发布测试速度指令
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.5}}"
```

### 3. 查看串口数据

可以使用串口调试工具查看发送的数据：

```bash
# 使用minicom
sudo apt-get install minicom
sudo minicom -D /dev/ttyUSB0 -b 115200

# 或使用screen
screen /dev/ttyUSB0 115200
```

## 协议修改

如果您的下位机使用不同的协议格式，需要修改 `src/serial_driver_node.cpp` 中的以下函数：

1. `sendVelocityCommand()` - 修改协议格式
2. 可能需要添加接收下位机反馈的功能

## 故障排除

1. **串口打开失败**
   - 检查设备路径是否正确
   - 检查权限设置
   - 检查串口是否被其他程序占用

2. **数据发送失败**
   - 检查波特率是否匹配
   - 检查串口线连接
   - 查看日志输出

3. **下位机无响应**
   - 检查协议格式是否匹配
   - 检查数据字节序（小端/大端）
   - 使用串口调试工具验证数据格式

## 作者

CSU-RM-Sentry Team

## 许可证

Apache-2.0
