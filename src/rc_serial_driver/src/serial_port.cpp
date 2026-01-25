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

  ssize_t bytes_written = ::write(fd_, data, size);
  if (bytes_written < 0) {
    if (errno != EAGAIN && errno != EWOULDBLOCK) {
      std::cerr << "Serial write error: " << strerror(errno) << std::endl;
    }
    return -1;
  }

  return static_cast<int>(bytes_written);
}

int SerialPort::read(uint8_t * data, size_t size)
{
  if (!isOpen() || data == nullptr || size == 0) {
    return -1;
  }

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

  return true;
}

}  // namespace rm_serial_driver
