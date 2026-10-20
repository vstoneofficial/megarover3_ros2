cmake_minimum_required(VERSION 3.8)
project(megarover3_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(builtin_interfaces REQUIRED)

# pub_odom
add_executable(pub_odom src/pub_odom.cpp)
target_compile_features(pub_odom PRIVATE cxx_std_17)
target_include_directories(pub_odom PRIVATE include)
ament_target_dependencies(
  pub_odom
  rcl_interfaces
  builtin_interfaces
  rclcpp
  geometry_msgs
  nav_msgs
  tf2_ros
)

# rover_gamepad
add_executable(rover_gamepad src/rover_gamepad.cpp)
ament_target_dependencies(
  rover_gamepad
  rclcpp
  geometry_msgs
  sensor_msgs
)

# rover_gamepad_tty
add_executable(rover_gamepad_tty src/rover_gamepad.cpp)
ament_target_dependencies(
  rover_gamepad_tty
  rclcpp
  geometry_msgs
  sensor_msgs
)

set(bringup_targets pub_odom rover_gamepad rover_gamepad_tty)

install(TARGETS ${bringup_targets}
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY launch rviz params
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
