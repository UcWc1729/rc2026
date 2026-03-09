#include "rm_serial_driver/serial_port.hpp"
#include <cstring>
#include <cerrno>
#include <iostream>

namespace rm_serial_driver
{

SerialPort::SerialPort()
: fd_(-1), is_open_(false)
{
}

SerialPort::~SerialPort()
{
  close();
}

bool SerialPort::open(const std::string & port_name, uint32_t baudrate)
{
  if (is_open_) {
    close();
  }

  port_name_ = port_name;

  // 打开串口设备（非阻塞模式）
  fd_ = ::open(port_name.c_str(), O_RDWR | O_NOCTTY | O_NONBLOCK);
  if (fd_ < 0) {
    std::cerr << "Failed to open serial port: " << port_name << " Error: " << strerror(errno) << std::endl;
    return false;
  }

  // 配置串口参数
  if (!configure(baudrate)) {
    ::close(fd_);
    fd_ = -1;
    return false;
  }

  is_open_ = true;
  return true;
}

void SerialPort::close()
{
  if (fd_ >= 0) {
    ::close(fd_);
    fd_ = -1;
  }
  is_open_ = false;
}

bool SerialPort::isOpen() const
{
  return is_open_ && (fd_ >= 0);
}

int SerialPort::write(const uint8_t * data, size_t size)
{
  if (!isOpen() || data == nullptr || size == 0) {
    return -1;
  }

  // 非阻塞模式写入数据（与Serial_test版本一致：写入后flush，不清空）
  ssize_t bytes_written = ::write(fd_, data, size);
  
  // 如果写入失败且是因为缓冲区满（EAGAIN/EWOULDBLOCK）
  if (bytes_written < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
    // 清空输出缓冲区，丢弃旧数据（因为我们要发送的是最新数据）
    tcflush(fd_, TCOFLUSH);
    
    // 重试一次写入
    bytes_written = ::write(fd_, data, size);
    
    // 如果还是失败，返回错误
    if (bytes_written < 0) {
      return -1;
    }
  } else if (bytes_written < 0) {
    // 其他错误，打印日志
    std::cerr << "Serial write error: " << strerror(errno) << std::endl;
    return -1;
  }

  // 检查是否完整写入
  if (static_cast<size_t>(bytes_written) < size) {
    // 部分写入，尝试写入剩余数据
    size_t remaining = size - bytes_written;
    ssize_t ret = ::write(fd_, data + bytes_written, remaining);
    if (ret > 0) {
      bytes_written += ret;
    }
  }

  // 确保数据立即发送到硬件（与Serial_test版本的flush()一致）
  // 使用tcdrain等待所有数据发送完成，类似Python的serial.flush()
  if (bytes_written > 0) {
    tcdrain(fd_);  // 阻塞等待所有数据发送完成
  }

  return static_cast<int>(bytes_written);
}

int SerialPort::read(uint8_t * data, size_t size)
{
  if (!isOpen() || data == nullptr || size == 0) {
    return -1;
  }

  // 非阻塞模式读取数据
  ssize_t bytes_read = ::read(fd_, data, size);
  if (bytes_read < 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK) {
      std::cerr << "Serial read error: " << strerror(errno) << std::endl;
    }
    return -1;
  }

  return static_cast<int>(bytes_read);
}

void SerialPort::flush()
{
  if (isOpen()) {
    tcflush(fd_, TCIOFLUSH);
  }
}

bool SerialPort::configure(uint32_t baudrate)
{
  struct termios tty;
  memset(&tty, 0, sizeof(tty));

  // 获取当前串口配置
  if (tcgetattr(fd_, &tty) != 0) {
    std::cerr << "Error getting serial port attributes: " << strerror(errno) << std::endl;
    return false;
  }

  // 设置波特率
  speed_t speed;
  switch (baudrate) {
    case 9600:
      speed = B9600;
      break;
    case 19200:
      speed = B19200;
      break;
    case 38400:
      speed = B38400;
      break;
    case 57600:
      speed = B57600;
      break;
    case 115200:
      speed = B115200;
      break;
    case 230400:
      speed = B230400;
      break;
    case 460800:
      speed = B460800;
      break;
    case 921600:
      speed = B921600;
      break;
    default:
      std::cerr << "Unsupported baudrate: " << baudrate << std::endl;
      return false;
  }

  cfsetospeed(&tty, speed);
  cfsetispeed(&tty, speed);

  // 8N1: 8位数据位，无校验，1位停止位
  tty.c_cflag &= ~PARENB;  // 无校验位
  tty.c_cflag &= ~CSTOPB;  // 1位停止位
  tty.c_cflag &= ~CSIZE;    // 清除数据位设置
  tty.c_cflag |= CS8;       // 8位数据位
  tty.c_cflag |= CREAD | CLOCAL;  // 启用接收，忽略调制解调器控制线

  // 禁用硬件流控
  tty.c_cflag &= ~CRTSCTS;

  // 原始输入模式
  tty.c_lflag &= ~(ICANON | ECHO | ECHOE | ISIG);

  // 原始输出模式
  tty.c_oflag &= ~OPOST;

  // 禁用输出缓冲（确保数据立即发送，不被缓冲）
  // 这可以避免数据被内核缓冲，立即发送到下位机
  tty.c_oflag &= ~ONLCR;  // 不转换换行符
  tty.c_oflag &= ~OCRNL;  // 不转换回车符

  // 读取超时设置
  tty.c_cc[VMIN] = 0;   // 最小读取字符数
  tty.c_cc[VTIME] = 10; // 超时时间（0.1秒）

  // 应用配置
  if (tcsetattr(fd_, TCSANOW, &tty) != 0) {
    std::cerr << "Error setting serial port attributes: " << strerror(errno) << std::endl;
    return false;
  }

  // 清空缓冲区
  tcflush(fd_, TCIOFLUSH);

  // 设置串口缓冲区大小（减小缓冲区，确保数据立即发送）
  struct serial_struct ser_info;
  if (ioctl(fd_, TIOCGSERIAL, &ser_info) == 0) {
    // 设置较小的缓冲区大小（默认通常是4096，改为512或更小）
    ser_info.xmit_fifo_size = 64;   // 发送缓冲区：64字节（最小）
    ser_info.flags |= ASYNC_LOW_LATENCY;  // 启用低延迟模式
    
    if (ioctl(fd_, TIOCSSERIAL, &ser_info) != 0) {
      std::cerr << "Warning: Failed to set serial buffer size: " << strerror(errno) << std::endl;
      // 继续执行，不影响串口使用
    } else {
      std::cerr << "Serial buffer size set to: " << ser_info.xmit_fifo_size << " bytes" << std::endl;
    }
  } else {
    std::cerr << "Warning: Failed to get serial info: " << strerror(errno) << std::endl;
    // 继续执行，不影响串口使用
  }

  return true;
}

}  // namespace rm_serial_driver
