// Copyright 2026 Vstone Co., Ltd.
// SPDX-License-Identifier: Apache-2.0
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "geometry_msgs/msg/pose_stamped.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "megarover3_bringup/firmware_odometry.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/msg/parameter_descriptor.hpp"
#include "tf2_ros/transform_broadcaster.hpp"

using megarover3_bringup::FirmwareOdometrySynchronizer;
using megarover3_bringup::FirmwarePose;
using megarover3_bringup::FirmwareTwist;
using megarover3_bringup::SampleResult;
using megarover3_bringup::SampleStatus;
using megarover3_bringup::SynchronizerConfig;

class PubOdomNode : public rclcpp::Node
{
public:
  PubOdomNode()
  : Node("odometry_publisher")
  {
    rcl_interfaces::msg::ParameterDescriptor descriptor;
    descriptor.read_only = true;  // Configuration changes require a node restart.
    const auto queue_size = declare_parameter<int64_t>("sync_queue_size", 50, descriptor);
    if (queue_size < 1 || queue_size > 1000) {
      throw std::invalid_argument("sync_queue_size must be in [1, 1000]");
    }
    SynchronizerConfig config;
    config.queue_size = static_cast<std::size_t>(queue_size);
    config.pair_timeout_ns = duration_parameter("pair_timeout_sec", 0.1, false, descriptor);
    config.max_sample_age_ns = duration_parameter("max_sample_age_sec", 0.5, false, descriptor);
    config.future_tolerance_ns = duration_parameter("future_tolerance_sec", 0.1, true, descriptor);
    synchronizer_ = std::make_unique<FirmwareOdometrySynchronizer>(config);
    publish_tf_ = declare_parameter<bool>("publish_tf", true, descriptor);
    pose_covariance_ = covariance_parameter(
      "pose_covariance_diagonal", {0.01, 0.01, 1e6, 1e6, 1e6, 0.1}, descriptor);
    twist_covariance_ = covariance_parameter(
      "twist_covariance_diagonal", {0.01, 1e6, 1e6, 1e6, 1e6, 0.1}, descriptor);

    publisher_ = create_publisher<nav_msgs::msg::Odometry>("odom", rclcpp::QoS(10));
    if (publish_tf_) {
      tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    }
    const auto qos = rclcpp::SensorDataQoS().keep_last(config.queue_size);
    pose_subscription_ = create_subscription<geometry_msgs::msg::PoseStamped>(
      "rover_pos_stamped", qos,
      [this](geometry_msgs::msg::PoseStamped::ConstSharedPtr msg) {
        if (msg->header.frame_id != "odom") {
          warn("Pose frame must be odom");
          return;
        }
        const auto & p = msg->pose.position;
        const auto & q = msg->pose.orientation;
        handle(synchronizer_->add_pose(
            stamp_ns(msg->header.stamp), FirmwarePose{{p.x, p.y, p.z}, {q.x, q.y, q.z, q.w}},
            now().nanoseconds(), steady_now_ns()));
      });
    twist_subscription_ = create_subscription<geometry_msgs::msg::TwistStamped>(
      "rover_twist_stamped", qos,
      [this](geometry_msgs::msg::TwistStamped::ConstSharedPtr msg) {
        if (msg->header.frame_id != "base_footprint") {
          warn("Firmware Twist frame must be base_footprint");
          return;
        }
        const auto & v = msg->twist.linear;
        const auto & w = msg->twist.angular;
        handle(synchronizer_->add_twist(
            stamp_ns(msg->header.stamp), FirmwareTwist{{v.x, v.y, v.z}, {w.x, w.y, w.z}},
            now().nanoseconds(), steady_now_ns()));
      });
    timer_ = create_wall_timer(std::chrono::milliseconds(100), [this]() {
          if (synchronizer_->advance(now().nanoseconds(), steady_now_ns())) {
            warn("ROS clock moved backward; discarded pending odometry and reset stamp watermark");
          }
      });
    RCLCPP_INFO(
      get_logger(), "F120A wheel-center odometry: odom -> base_footprint; exact stamp pairs, "
      "Best Effort inputs, no output before a valid pair or during missing telemetry");
  }

private:
  static int64_t steady_now_ns()
  {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::steady_clock::now().time_since_epoch()).count();
  }

  static int64_t stamp_ns(const builtin_interfaces::msg::Time & stamp)
  {
    if (stamp.sec < 0 || stamp.nanosec >= 1000000000u) {
      return 0;
    }
    return static_cast<int64_t>(stamp.sec) * 1000000000LL + stamp.nanosec;
  }

  int64_t duration_parameter(
    const std::string & name, double default_value, bool allow_zero,
    const rcl_interfaces::msg::ParameterDescriptor & descriptor)
  {
    const double value = declare_parameter<double>(name, default_value, descriptor);
    if (!std::isfinite(value) || value > 10.0 ||
      (allow_zero ? value < 0.0 : value < 1e-6))
    {
      throw std::invalid_argument(name + " must be finite and in the documented seconds range");
    }
    return static_cast<int64_t>(value * 1e9);
  }

  std::array<double, 36> covariance_parameter(
    const std::string & name, const std::vector<double> & defaults,
    const rcl_interfaces::msg::ParameterDescriptor & descriptor)
  {
    const auto values = declare_parameter<std::vector<double>>(name, defaults, descriptor);
    if (values.size() != 6) {
      throw std::invalid_argument(name + " must contain six variances");
    }
    std::array<double, 36> covariance{};
    for (std::size_t i = 0; i < values.size(); ++i) {
      if (!std::isfinite(values[i]) || values[i] <= 0.0) {
        throw std::invalid_argument(name + " variances must be finite and positive");
      }
      covariance[i * 7] = values[i];
    }
    return covariance;
  }

  void warn(const char * reason)
  {
    RCLCPP_WARN_THROTTLE(get_logger(), steady_clock_, 5000, "%s", reason);
  }

  void handle(const SampleResult & result)
  {
    if (!result.sample) {
      if (result.status == SampleStatus::Invalid || result.status == SampleStatus::Stale ||
        result.status == SampleStatus::Future)
      {
        warn("Dropped invalid, stale or future firmware sample; check values and ROS time sync");
      }
      return;
    }
    const auto & sample = *result.sample;
    nav_msgs::msg::Odometry odom;
    odom.header.stamp = rclcpp::Time(sample.stamp_ns, RCL_ROS_TIME);
    odom.header.frame_id = "odom";
    odom.child_frame_id = "base_footprint";
    odom.pose.pose.position.x = sample.pose.position[0];
    odom.pose.pose.position.y = sample.pose.position[1];
    odom.pose.pose.position.z = sample.pose.position[2];
    odom.pose.pose.orientation.x = sample.pose.orientation[0];
    odom.pose.pose.orientation.y = sample.pose.orientation[1];
    odom.pose.pose.orientation.z = sample.pose.orientation[2];
    odom.pose.pose.orientation.w = sample.pose.orientation[3];
    odom.twist.twist.linear.x = sample.twist.linear[0];
    odom.twist.twist.angular.z = sample.twist.angular[2];
    odom.pose.covariance = pose_covariance_;
    odom.twist.covariance = twist_covariance_;
    publisher_->publish(odom);
    if (tf_broadcaster_) {
      geometry_msgs::msg::TransformStamped transform;
      transform.header = odom.header;
      transform.child_frame_id = odom.child_frame_id;
      transform.transform.translation.x = odom.pose.pose.position.x;
      transform.transform.translation.y = odom.pose.pose.position.y;
      transform.transform.translation.z = odom.pose.pose.position.z;
      transform.transform.rotation = odom.pose.pose.orientation;
      tf_broadcaster_->sendTransform(transform);
    }
  }

  rclcpp::Clock steady_clock_{RCL_STEADY_TIME};
  std::unique_ptr<FirmwareOdometrySynchronizer> synchronizer_;
  bool publish_tf_ = true;
  std::array<double, 36> pose_covariance_{};
  std::array<double, 36> twist_covariance_{};
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr publisher_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_subscription_;
  rclcpp::Subscription<geometry_msgs::msg::TwistStamped>::SharedPtr twist_subscription_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  int result = 0;
  try {
    rclcpp::spin(std::make_shared<PubOdomNode>());
  } catch (const std::exception & error) {
    RCLCPP_FATAL(rclcpp::get_logger("pub_odom"), "%s", error.what());
    result = 1;
  }
  rclcpp::shutdown();
  return result;
}
