# 串口通信协议说明

## 协议格式

本驱动使用的串口协议格式如下：

### 速度指令帧格式

```
字节位置 | 内容        | 说明                    | 值
---------|------------|------------------------|----------
0        | 帧头1      | 固定值                  | 0xAA
1        | 帧头2      | 固定值                  | 0xBB
2        | 数据长度   | 数据部分字节数          | 0x06
3        | vx_low     | 线速度x低字节           | uint8_t
4        | vx_high    | 线速度x高字节           | uint8_t
5        | vy_low     | 线速度y低字节           | uint8_t
6        | vy_high    | 线速度y高字节           | uint8_t
7        | vtheta_low | 角速度低字节             | uint8_t
8        | vtheta_high| 角速度高字节             | uint8_t
9        | 校验和     | 前9字节的累加和         | uint8_t
```

### 数据格式说明

1. **速度单位**:
   - 线速度 (vx, vy): `mm/s` (ROS中的m/s × 1000)
   - 角速度 (vtheta): `0.001 rad/s` (ROS中的rad/s × 1000)

2. **字节序**: 小端序 (Little Endian)
   - 例如: 速度值 `1000 mm/s` (0x03E8)
     - 低字节: `0xE8`
     - 高字节: `0x03`

3. **校验和**: 简单累加校验
   ```cpp
   checksum = sum(bytes[0..8]) & 0xFF
   ```

### 示例

假设要发送速度指令: `vx = 0.5 m/s`, `vy = 0.0 m/s`, `vtheta = 0.3 rad/s`

1. 转换为整数:
   - `vx = 0.5 × 1000 = 500 mm/s = 0x01F4`
   - `vy = 0.0 × 1000 = 0 mm/s = 0x0000`
   - `vtheta = 0.3 × 1000 = 300 = 0x012C`

2. 构建数据帧:
   ```
   0xAA 0xBB 0x06 0xF4 0x01 0x00 0x00 0x2C 0x01 [checksum]
   ```

3. 计算校验和:
   ```
   checksum = 0xAA + 0xBB + 0x06 + 0xF4 + 0x01 + 0x00 + 0x00 + 0x2C + 0x01
            = 0x383 & 0xFF
            = 0x83
   ```

4. 完整帧:
   ```
   0xAA 0xBB 0x06 0xF4 0x01 0x00 0x00 0x2C 0x01 0x83
   ```

## 修改协议

如果您的下位机使用不同的协议格式，需要修改 `src/serial_driver_node.cpp` 中的 `sendVelocityCommand()` 函数。

常见修改点：

1. **帧头**: 修改 `FRAME_HEADER1` 和 `FRAME_HEADER2`
2. **数据格式**: 修改速度值的编码方式（单位、字节序等）
3. **校验方式**: 修改校验和算法（CRC、异或等）
4. **帧尾**: 如果需要，添加帧尾字节

## 下位机接收示例（伪代码）

```cpp
// 下位机接收示例（C/C++）
uint8_t buffer[10];
uint8_t received = 0;

while (received < 10) {
    received += serial_read(buffer + received, 10 - received);
}

// 检查帧头
if (buffer[0] == 0xAA && buffer[1] == 0xBB) {
    // 解析速度值（小端序）
    int16_t vx = buffer[3] | (buffer[4] << 8);
    int16_t vy = buffer[5] | (buffer[6] << 8);
    int16_t vtheta = buffer[7] | (buffer[8] << 8);
    
    // 转换为实际单位
    float vx_mps = vx / 1000.0f;      // mm/s -> m/s
    float vy_mps = vy / 1000.0f;      // mm/s -> m/s
    float vtheta_radps = vtheta / 1000.0f;  // 0.001 rad/s -> rad/s
    
    // 验证校验和
    uint8_t checksum = 0;
    for (int i = 0; i < 9; i++) {
        checksum += buffer[i];
    }
    
    if (checksum == buffer[9]) {
        // 校验通过，使用速度值
        // 控制电机...
    }
}
```
