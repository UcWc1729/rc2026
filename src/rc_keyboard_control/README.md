# rc_keyboard_control

键盘控制节点，用于通过键盘控制机器人底盘移动。

## 功能

- 通过键盘控制机器人前后左右移动和旋转
- 支持组合按键（如同时前进和左转）
- 支持全向轮模式（横向移动）
- 按键按下时移动，松开时停止
- **完全适配通用上下位机通信协议 v1.0**

## 协议适配说明

本节点通过标准的ROS2消息接口与串口驱动节点通信，**完全适配通用上下位机通信协议**：

### 数据流

```
键盘控制节点
    ↓ (发布 geometry_msgs/Twist)
/cmd_vel 话题
    ↓ (订阅并转换)
串口驱动节点 (rc_serial_driver)
    ↓ (协议打包)
通用上下位机通信协议 v1.0
    ↓ (串口发送)
STM32下位机
```

### 协议详情

- **命令ID**: `CMD_CHASSIS_SPEED (0x0101)`
- **数据格式**: 
  ```c
  typedef struct {
      float vx;       // 前进速度 (m/s)
      float vy;       // 横向速度 (m/s)
      float wz;       // 旋转角速度 (rad/s)
  } ChassisSpeedCmd;  // 12字节
  ```
- **协议帧格式**: 
  ```
  SOF(0xA5) + LEN(2B) + SEQ(1B) + CRC8(1B) + CMD_ID(2B) + DATA(12B) + CRC16(2B)
  ```
- **校验**: 双重CRC校验（CRC8帧头校验 + CRC16整帧校验）
- **序列号**: 自动管理，0-255循环

详细协议说明请参考项目根目录的 `通用上下位机通信协议设计文档.md`

## 键盘控制说明

### 基础控制（差速轮/麦克纳姆轮）

| 按键 | 功能 |
|------|------|
| **W** | 前进 |
| **S** | 后退 |
| **A** | 左转 |
| **D** | 右转 |
| **Q** | 逆时针旋转 |
| **E** | 顺时针旋转 |
| **空格** | 停止 |
| **Ctrl+C** | 退出程序 |

### 全向轮模式（enable_lateral=true）

| 按键 | 功能 |
|------|------|
| **W** | 前进 |
| **S** | 后退 |
| **A** | 左移 |
| **D** | 右移 |
| **Q** | 逆时针旋转 |
| **E** | 顺时针旋转 |
| **空格** | 停止 |
| **Ctrl+C** | 退出程序 |

### 组合按键

可以同时按下多个按键实现组合运动，例如：
- **W + A**: 前进并左转
- **W + Q**: 前进并逆时针旋转
- **W + D + E**: 前进、右转并顺时针旋转

## 安装

### 1. 编译包

```bash
cd ~/ROBOCON2026/lidar_test/rc2026
colcon build --packages-select rc_keyboard_control
source install/setup.bash
```

## 使用方法

**重要提示**: 键盘控制节点**必须从终端直接运行**，不能通过launch文件启动，因为需要访问终端输入设备。

### 方法1: 使用启动脚本（推荐）

```bash
# 差速轮模式
./keyboard_control.sh

# 全向轮模式
./keyboard_control.sh lateral
```

### 方法2: 直接运行节点

```bash
# 基础模式（差速轮）
ros2 run rc_keyboard_control keyboard_control_node

# 全向轮模式
ros2 run rc_keyboard_control keyboard_control_node \
    --ros-args -p enable_lateral:=true

# 自定义速度
ros2 run rc_keyboard_control keyboard_control_node \
    --ros-args \
    -p linear_speed:=0.8 \
    -p angular_speed:=1.0
```

### 方法3: 带完整参数运行

```bash
ros2 run rc_keyboard_control keyboard_control_node \
    --ros-args \
    -p cmd_vel_topic:=/cmd_vel \
    -p linear_speed:=0.5 \
    -p angular_speed:=0.5 \
    -p enable_lateral:=false \
    -p publish_rate:=20.0
```

### ⚠️ 注意

- **不能使用launch文件启动**，因为launch文件启动的进程没有连接到终端，无法读取键盘输入
- 必须从真实的终端窗口运行节点
- 确保运行节点的终端窗口处于焦点状态，才能接收键盘输入

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cmd_vel_topic` | string | `/cmd_vel` | 速度指令话题名称 |
| `linear_speed` | double | `0.5` | 线速度 (m/s) |
| `angular_speed` | double | `0.5` | 角速度 (rad/s) |
| `enable_lateral` | bool | `false` | 是否启用横向移动（全向轮） |
| `publish_rate` | double | `20.0` | 发布频率 (Hz) |

## 使用示例

### 示例1: 基础控制

1. 启动串口驱动（在一个终端窗口）：
```bash
ros2 launch rc_serial_driver serial_driver.launch.py
```

2. 启动键盘控制（在另一个终端窗口）：
```bash
./keyboard_control.sh
# 或者
ros2 run rc_keyboard_control keyboard_control_node
```

3. 在键盘控制终端中按 **W** 键前进，按 **S** 键后退。

### 示例2: 全向轮机器人

```bash
# 在终端中运行
ros2 run rc_keyboard_control keyboard_control_node \
    --ros-args \
    -p enable_lateral:=true \
    -p linear_speed:=0.8 \
    -p angular_speed:=1.0
```

### 示例3: 高速度控制

```bash
ros2 run rc_keyboard_control keyboard_control_node \
    --ros-args \
    -p linear_speed:=1.5 \
    -p angular_speed:=2.0
```

## 注意事项

1. **终端焦点**: 键盘控制需要在运行节点的终端窗口中操作，确保该窗口处于焦点状态。

2. **权限**: 如果串口驱动需要权限，确保已正确设置：
```bash
sudo usermod -a -G dialout $USER
# 然后重新登录
```

3. **组合按键**: 可以同时按下多个按键实现组合运动，松开按键后该方向的速度会停止。

4. **安全**: 程序退出时会自动发送停止指令，但建议在停止前按空格键确保机器人停止。

5. **速度限制**: 速度会被串口驱动节点的 `max_linear_vel` 和 `max_angular_vel` 参数限制。

## 故障排除

### 问题1: 按键无响应

- 确保键盘控制节点所在的终端窗口处于焦点状态
- 检查节点是否正常运行：`ros2 node list`
- 查看日志：`ros2 topic echo /cmd_vel`

### 问题2: 机器人不移动

- 检查串口驱动是否运行：`ros2 node list | grep serial_driver`
- 检查话题连接：`ros2 topic list` 和 `ros2 topic info /cmd_vel`
- 检查串口连接和权限

### 问题3: 速度太快或太慢

- 调整 `linear_speed` 和 `angular_speed` 参数
- 检查串口驱动节点的 `max_linear_vel` 和 `max_angular_vel` 限制

## 依赖

- `rclpy`: ROS2 Python客户端库
- `geometry_msgs`: ROS2几何消息类型

## 作者

CSU-RM-Sentry Team

## 许可证

Apache-2.0
