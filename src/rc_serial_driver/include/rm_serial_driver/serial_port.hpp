#ifndef RM_SERIAL_DRIVER__SERIAL_PORT_HPP_
#define RM_SERIAL_DRIVER__SERIAL_PORT_HPP_

#include <string>
#include <cstdint>
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>

namespace rm_serial_driver
{

class SerialPort
{
public:
  SerialPort();
  ~SerialPort();

  /**
   * @brief 打开串口
   * @param port_name 串口设备路径，如 "/dev/ttyUSB0"
   * @param baudrate 波特率，如 115200
   * @return true 成功，false 失败
   */
  bool open(const std::string & port_name, uint32_t baudrate);

  /**
   * @brief 关闭串口
   */
  void close();

  /**
   * @brief 检查串口是否打开
   * @return true 已打开，false 未打开
   */
  bool isOpen() const;

  /**
   * @brief 发送数据
   * @param data 数据指针
   * @param size 数据大小（字节）
   * @return 实际发送的字节数，-1表示失败
   */
  int write(const uint8_t * data, size_t size);

  /**
   * @brief 读取数据
   * @param data 数据缓冲区
   * @param size 缓冲区大小
   * @return 实际读取的字节数，-1表示失败
   */
  int read(uint8_t * data, size_t size);

  /**
   * @brief 清空接收缓冲区
   */
  void flush();

private:
  int fd_;  // 文件描述符
  bool is_open_;  // 是否打开
  std::string port_name_;  // 串口名称

  /**
   * @brief 配置串口参数
   * @param baudrate 波特率
   * @return true 成功，false 失败
   */
  bool configure(uint32_t baudrate);
};

}  // namespace rm_serial_driver

#endif  // RM_SERIAL_DRIVER__SERIAL_PORT_HPP_
