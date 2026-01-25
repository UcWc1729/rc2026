#ifndef RM_SERIAL_DRIVER__PROTOCOL_HPP_
#define RM_SERIAL_DRIVER__PROTOCOL_HPP_

#include <cstdint>
#include <cstring>

namespace rm_serial_driver
{

// 协议常量定义
#define FRAME_HEADER_SOF        0xA5
#define FRAME_MAX_DATA_LEN      64
#define FRAME_MIN_LEN           9  // 最小帧长度: 5(header) + 2(cmd_id) + 2(crc16)

// 命令ID定义
namespace CmdID
{
  // 上位机 → 下位机
  constexpr uint16_t CHASSIS_SPEED = 0x0101;      // 底盘速度控制
  constexpr uint16_t CHASSIS_POSITION = 0x0102;   // 底盘位置控制
  constexpr uint16_t CHASSIS_MODE = 0x0103;       // 底盘模式切换
  constexpr uint16_t HEARTBEAT = 0x0FFF;         // 心跳包
  
  // 下位机 → 上位机
  constexpr uint16_t CHASSIS_FEEDBACK = 0x8101;   // 底盘反馈
  constexpr uint16_t CHASSIS_ODOM = 0x8102;       // 里程计数据
  constexpr uint16_t SYSTEM_STATUS = 0xF001;      // 系统状态
}

// 帧头结构 (5字节)
#pragma pack(push, 1)
struct FrameHeader
{
  uint8_t sof;           // 起始字节 0xA5
  uint16_t data_length;  // 数据段长度 (cmd_id + data)
  uint8_t seq;           // 包序号 (0-255循环)
  uint8_t crc8;          // 帧头CRC8校验
};
#pragma pack(pop)

/**
 * @brief 计算CRC8校验
 * @param data 数据指针
 * @param length 数据长度
 * @return CRC8值
 */
uint8_t calculateCRC8(const uint8_t * data, uint16_t length);

/**
 * @brief 计算CRC16校验 (MODBUS标准)
 * @param data 数据指针
 * @param length 数据长度
 * @return CRC16值
 */
uint16_t calculateCRC16(const uint8_t * data, uint16_t length);

/**
 * @brief 打包数据帧
 * @param cmd_id 命令ID
 * @param data 数据指针
 * @param data_len 数据长度 (0-64字节)
 * @param seq 序列号 (0-255)
 * @param out_buffer 输出缓冲区 (需至少 9+data_len 字节)
 * @return 打包后的总长度，失败返回0
 */
uint16_t packFrame(uint16_t cmd_id, const uint8_t * data, uint16_t data_len, 
                   uint8_t seq, uint8_t * out_buffer);

/**
 * @brief 解析数据帧
 * @param buffer 接收缓冲区
 * @param length 接收长度
 * @param cmd_id 输出命令ID指针
 * @param data 输出数据指针
 * @param data_len 输出数据长度指针
 * @param seq 输出序列号指针
 * @return true=成功, false=失败
 */
bool parseFrame(const uint8_t * buffer, uint16_t length,
                uint16_t * cmd_id, const uint8_t ** data, uint16_t * data_len, uint8_t * seq);

}  // namespace rm_serial_driver

#endif  // RM_SERIAL_DRIVER__PROTOCOL_HPP_
