#include "rm_serial_driver/protocol.hpp"
#include <iostream>

namespace rm_serial_driver
{

uint8_t calculateCRC8(const uint8_t * data, uint16_t length)
{
  uint8_t crc = 0xFF;  // 初始值
  
  for (uint16_t i = 0; i < length; i++) {
    crc ^= data[i];
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x80) {
        crc = (crc << 1) ^ 0x31;  // 多项式
      } else {
        crc <<= 1;
      }
    }
  }
  
  return crc;
}

uint16_t calculateCRC16(const uint8_t * data, uint16_t length)
{
  uint16_t crc = 0xFFFF;  // 初始值
  
  for (uint16_t i = 0; i < length; i++) {
    crc ^= data[i];
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x0001) {
        crc = (crc >> 1) ^ 0xA001;  // MODBUS多项式
      } else {
        crc >>= 1;
      }
    }
  }
  
  return crc;
}

uint16_t packFrame(uint16_t cmd_id, const uint8_t * data, uint16_t data_len, 
                   uint8_t seq, uint8_t * out_buffer)
{
  if (data_len > FRAME_MAX_DATA_LEN) {
    return 0;  // 数据长度超限
  }
  
  if (out_buffer == nullptr) {
    return 0;
  }
  
  uint16_t payload_len = 2 + data_len;  // cmd_id(2) + data
  
  // 1. 填充帧头 (不含CRC8)
  FrameHeader header;
  header.sof = FRAME_HEADER_SOF;
  header.data_length = payload_len;
  header.seq = seq;
  
  // 2. 计算帧头CRC8 (对 data_length + seq 共4字节)
  // 按照协议文档，CRC8计算data_length(2字节) + seq(1字节) + padding(1字节) = 4字节
  uint8_t header_data[4];
  header_data[0] = payload_len & 0xFF;        // data_length 低字节
  header_data[1] = (payload_len >> 8) & 0xFF; // data_length 高字节
  header_data[2] = seq;                       // seq
  header_data[3] = 0;                         // padding
  header.crc8 = calculateCRC8(header_data, 4);
  
  // 3. 拷贝帧头
  memcpy(out_buffer, &header, sizeof(FrameHeader));
  
  // 4. 填充命令ID (小端序)
  out_buffer[5] = cmd_id & 0xFF;
  out_buffer[6] = (cmd_id >> 8) & 0xFF;
  
  // 5. 拷贝数据段
  if (data_len > 0 && data != nullptr) {
    memcpy(&out_buffer[7], data, data_len);
  }
  
  // 6. 计算整帧CRC16 (从SOF到DATA末尾)
  uint16_t total_len = 7 + data_len;
  uint16_t crc16 = calculateCRC16(out_buffer, total_len);
  out_buffer[total_len] = crc16 & 0xFF;        // 低字节
  out_buffer[total_len + 1] = (crc16 >> 8) & 0xFF;  // 高字节
  
  return total_len + 2;  // 返回总长度
}

bool parseFrame(const uint8_t * buffer, uint16_t length,
                uint16_t * cmd_id, const uint8_t ** data, uint16_t * data_len, uint8_t * seq)
{
  // 1. 检查最小长度
  if (length < FRAME_MIN_LEN) {
    return false;
  }
  
  // 2. 检查帧头标志
  if (buffer[0] != FRAME_HEADER_SOF) {
    return false;
  }
  
  // 3. 解析帧头
  FrameHeader * header = (FrameHeader *)buffer;
  
  // 4. 验证帧头CRC8
  uint8_t header_data[4];
  header_data[0] = header->data_length & 0xFF;
  header_data[1] = (header->data_length >> 8) & 0xFF;
  header_data[2] = header->seq;
  header_data[3] = 0;
  uint8_t crc8_calc = calculateCRC8(header_data, 4);
  if (crc8_calc != header->crc8) {
    return false;
  }
  
  // 5. 检查长度是否匹配
  uint16_t expected_len = 5 + header->data_length + 2;  // header + payload + crc16
  if (length != expected_len) {
    return false;
  }
  
  // 6. 验证整帧CRC16
  uint16_t crc16_calc = calculateCRC16(buffer, length - 2);
  uint16_t crc16_recv = buffer[length - 2] | (buffer[length - 1] << 8);
  if (crc16_calc != crc16_recv) {
    return false;
  }
  
  // 7. 提取命令ID (小端序)
  *cmd_id = buffer[5] | (buffer[6] << 8);
  
  // 8. 提取序列号
  if (seq != nullptr) {
    *seq = header->seq;
  }
  
  // 9. 提取数据段
  *data_len = header->data_length - 2;  // 减去cmd_id的2字节
  if (*data_len > 0) {
    *data = &buffer[7];
  } else {
    *data = nullptr;
  }
  
  return true;
}

}  // namespace rm_serial_driver
