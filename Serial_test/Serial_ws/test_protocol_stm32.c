/**
 * @file test_protocol.c
 * @brief 下位机协议测试代码 - 粘贴到STM32 main.c中测试
 * @date 2026-01-23
 */

/* 将此代码添加到STM32项目中进行测试 */

// ========== 1. 包含头文件 ==========
#include "protocol_chassis.h"
#include <stdio.h>

// ========== 2. 全局变量 ==========
uint8_t rx_buffer[256];
uint16_t rx_index = 0;

// ========== 3. 回调函数实现 ==========

// 底盘速度控制回调
void handle_chassis_speed(float vx, float vy, float wz)
{
    // 添加调试输出
    printf("✓ 收到速度命令:\r\n");
    printf("  Vx = %.3f m/s\r\n", vx);
    printf("  Vy = %.3f m/s\r\n", vy);
    printf("  Wz = %.3f rad/s\r\n", wz);
    
    // TODO: 在这里控制电机
    // 示例:
    // Motor_SetSpeed(MOTOR_FL, vx + vy + wz);
    // Motor_SetSpeed(MOTOR_FR, vx - vy - wz);
    // Motor_SetSpeed(MOTOR_RL, vx - vy + wz);
    // Motor_SetSpeed(MOTOR_RR, vx + vy - wz);
}

// 底盘停止回调
void handle_chassis_stop(void)
{
    printf("✓ 收到停止命令\r\n");
    
    // TODO: 停止所有电机
    // Motor_StopAll();
}

// 心跳包回调
void handle_heartbeat(void)
{
    // 可选：打印心跳信息（太频繁可能影响性能）
    // printf("心跳\r\n");
}

// ========== 4. 初始化函数（在main中调用）==========
void Protocol_Setup(void)
{
    // 初始化协议
    Protocol_Init();
    
    // 注册回调函数
    Protocol_Callbacks callbacks = {
        .on_chassis_speed = handle_chassis_speed,
        .on_chassis_stop = handle_chassis_stop,
        .on_heartbeat = handle_heartbeat
    };
    Protocol_RegisterCallbacks(&callbacks);
    
    printf("✓ 协议初始化完成\r\n");
}

// ========== 5. UART接收处理 ==========

// 方式A: 使用DMA接收（推荐）
void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart6)  // 根据你的串口修改
    {
        // 处理接收到的数据
        Protocol_ProcessData(rx_buffer, rx_index);
        
        // 重新启动DMA接收
        rx_index = 0;
        HAL_UART_Receive_DMA(&huart6, rx_buffer, sizeof(rx_buffer));
    }
}

// 方式B: 使用中断接收
uint8_t rx_byte;

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if (huart == &huart6)
    {
        // 存储接收的字节
        if (rx_index < sizeof(rx_buffer))
        {
            rx_buffer[rx_index++] = rx_byte;
            
            // 检查是否收到完整帧
            if (rx_index >= 9)  // 最小帧长度
            {
                // 查找帧头
                for (uint16_t i = 0; i < rx_index; i++)
                {
                    if (rx_buffer[i] == 0xA5)
                    {
                        // 可能是帧头
                        if (rx_index - i >= 5)
                        {
                            FrameHeader *header = (FrameHeader*)&rx_buffer[i];
                            uint16_t frame_len = 5 + header->data_length + 2;
                            
                            if (rx_index - i >= frame_len)
                            {
                                // 数据足够，尝试解析
                                Protocol_ProcessData(&rx_buffer[i], frame_len);
                                
                                // 移除已处理的数据
                                rx_index = 0;
                                break;
                            }
                        }
                    }
                }
                
                // 缓冲区快满了，清空
                if (rx_index > sizeof(rx_buffer) - 50)
                {
                    rx_index = 0;
                }
            }
        }
        else
        {
            rx_index = 0;  // 缓冲区溢出，重置
        }
        
        // 继续接收下一个字节
        HAL_UART_Receive_IT(&huart6, &rx_byte, 1);
    }
}

// ========== 6. 测试函数 ==========

// 测试发送反馈数据
void Test_SendFeedback(void)
{
    static uint8_t tx_buffer[128];
    
    ChassisFeedback feedback;
    feedback.timestamp = HAL_GetTick();
    feedback.velocity_x = 0.1f;
    feedback.velocity_y = 0.0f;
    feedback.angular_vel = 0.0f;
    feedback.motor_speed[0] = 100.0f;
    feedback.motor_speed[1] = 100.0f;
    feedback.motor_speed[2] = 100.0f;
    feedback.motor_speed[3] = 100.0f;
    feedback.status = 0x01;
    
    uint16_t len = Protocol_PackFrame(
        CMD_CHASSIS_FEEDBACK,
        (uint8_t*)&feedback,
        sizeof(ChassisFeedback),
        0,
        tx_buffer
    );
    
    HAL_UART_Transmit(&huart6, tx_buffer, len, 100);
    printf("✓ 发送反馈数据 %d 字节\r\n", len);
}

// ========== 7. 在main函数中的使用示例 ==========

/*
int main(void)
{
    // 系统初始化
    HAL_Init();
    SystemClock_Config();
    
    // 外设初始化
    MX_GPIO_Init();
    MX_USART6_UART_Init();  // 根据你的串口修改
    MX_DMA_Init();          // 如果使用DMA
    
    // 协议初始化
    Protocol_Setup();
    
    // 启动UART接收
    // 方式A: DMA
    HAL_UART_Receive_DMA(&huart6, rx_buffer, sizeof(rx_buffer));
    
    // 或方式B: 中断
    // HAL_UART_Receive_IT(&huart6, &rx_byte, 1);
    
    printf("系统启动，等待上位机命令...\r\n");
    
    // 主循环
    while (1)
    {
        // 可选：定时发送反馈
        static uint32_t last_feedback_time = 0;
        if (HAL_GetTick() - last_feedback_time > 100)  // 10Hz
        {
            Test_SendFeedback();
            last_feedback_time = HAL_GetTick();
        }
        
        HAL_Delay(10);
    }
}
*/

// ========== 8. 调试输出配置 ==========

// 如果还没有配置printf，添加以下代码：

#ifdef __GNUC__
#define PUTCHAR_PROTOTYPE int __io_putchar(int ch)
#else
#define PUTCHAR_PROTOTYPE int fputc(int ch, FILE *f)
#endif

PUTCHAR_PROTOTYPE
{
    HAL_UART_Transmit(&huart6, (uint8_t *)&ch, 1, 0xFFFF);  // 根据你的调试串口修改
    return ch;
}

// ========== 9. 快速测试清单 ==========

/*
测试步骤：

1. 编译并下载到STM32
2. 打开串口助手（连接调试串口，如USART1）
3. 运行上位机程序：python3 continuous_send.py
4. 观察串口助手输出

预期输出：
  ✓ 协议初始化完成
  系统启动，等待上位机命令...
  ✓ 收到速度命令:
    Vx = 0.100 m/s
    Vy = 0.000 m/s
    Wz = 0.000 rad/s

如果看到以上输出，说明：
  ✓ 串口通信正常
  ✓ 协议解析正确
  ✓ 数据接收成功

如果没有输出：
  1. 检查波特率是否为115200
  2. 检查TX/RX是否接反
  3. 检查是否正确调用 Protocol_ProcessData()
  4. 在Protocol_ProcessData中添加更多调试输出
*/
