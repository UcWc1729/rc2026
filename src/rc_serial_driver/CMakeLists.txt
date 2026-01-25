cmake_minimum_required(VERSION 3.8)
project(rc_serial_driver)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(nav_msgs REQUIRED)

# Include directories
include_directories(include)

# Serial port class
add_library(serial_port SHARED
  src/serial_port.cpp
  src/protocol.cpp
)

ament_target_dependencies(serial_port
  rclcpp
)

# Serial driver node
add_executable(serial_driver_node
  src/serial_driver_node.cpp
)

ament_target_dependencies(serial_driver_node
  rclcpp
  geometry_msgs
  std_msgs
  nav_msgs
)

target_link_libraries(serial_driver_node
  serial_port
)

# Install
install(TARGETS
  serial_port
  serial_driver_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch/
  config/
  DESTINATION share/${PROJECT_NAME}/
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
