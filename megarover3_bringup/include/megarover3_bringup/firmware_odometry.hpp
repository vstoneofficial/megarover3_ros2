// Copyright 2026 Vstone Co., Ltd.
// SPDX-License-Identifier: Apache-2.0
#ifndef MEGAROVER3_BRINGUP__FIRMWARE_ODOMETRY_HPP_
#define MEGAROVER3_BRINGUP__FIRMWARE_ODOMETRY_HPP_

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <map>
#include <optional>
#include <stdexcept>

namespace megarover3_bringup
{

struct FirmwarePose
{
  std::array<double, 3> position{};
  std::array<double, 4> orientation{0.0, 0.0, 0.0, 1.0};  // x, y, z, w
};

struct FirmwareTwist
{
  std::array<double, 3> linear{};
  std::array<double, 3> angular{};
};

struct FirmwareSample
{
  int64_t stamp_ns;
  FirmwarePose pose;
  FirmwareTwist twist;
};

struct SynchronizerConfig
{
  std::size_t queue_size = 50;
  int64_t pair_timeout_ns = 100000000;
  int64_t max_sample_age_ns = 500000000;
  int64_t future_tolerance_ns = 100000000;
};

enum class SampleStatus {Waiting, Published, Invalid, Stale, Future, Duplicate};

struct SampleResult
{
  SampleStatus status;
  std::optional<FirmwareSample> sample;
};

// F120A firmware integrates differential-wheel motion at the wheel midpoint.
// Both pose and twist describe that point, regardless of the wire twist frame label.
// No host-side integration or timestamp substitution is performed here.
class FirmwareOdometrySynchronizer
{
public:
  explicit FirmwareOdometrySynchronizer(SynchronizerConfig config = {})
  : config_(config)
  {
    if (config.queue_size == 0 || config.queue_size > 1000 ||
      config.pair_timeout_ns <= 0 || config.max_sample_age_ns <= 0 ||
      config.max_sample_age_ns > 10000000000LL ||
      config.pair_timeout_ns > config.max_sample_age_ns ||
      config.future_tolerance_ns < 0 ||
      config.future_tolerance_ns > config.max_sample_age_ns)
    {
      throw std::invalid_argument("Invalid firmware odometry synchronization limits");
    }
  }

  // ROS time checks freshness; monotonic receipt time bounds matching waits.
  // A backward host ROS clock jump starts a new epoch, including its watermark.
  bool advance(int64_t ros_now_ns, int64_t steady_now_ns)
  {
    bool backward_jump = false;
    if (last_ros_now_ns_ && ros_now_ns < *last_ros_now_ns_) {
      pending_.clear();
      last_published_ns_.reset();
      backward_jump = true;
    } else if (last_ros_now_ns_ &&
      ros_now_ns - *last_ros_now_ns_ > config_.max_sample_age_ns)
    {
      pending_.clear();
    }
    last_ros_now_ns_ = ros_now_ns;
    for (auto it = pending_.begin(); it != pending_.end(); ) {
      if (steady_now_ns - it->second.first_receipt_ns > config_.pair_timeout_ns ||
        ros_now_ns - it->first > config_.max_sample_age_ns)
      {
        it = pending_.erase(it);
      } else {
        ++it;
      }
    }
    return backward_jump;
  }

  SampleResult add_pose(
    int64_t stamp_ns, const FirmwarePose & pose, int64_t ros_now_ns, int64_t steady_now_ns)
  {
    advance(ros_now_ns, steady_now_ns);
    if (!valid_pose(pose)) {
      return {SampleStatus::Invalid, std::nullopt};
    }
    const auto status = stamp_status(stamp_ns, ros_now_ns);
    if (status != SampleStatus::Waiting) {
      return {status, std::nullopt};
    }
    auto & pair = get_pair(stamp_ns, steady_now_ns);
    if (pair.pose) {
      return {SampleStatus::Duplicate, std::nullopt};
    }
    pair.pose = pose;
    return finish(stamp_ns);
  }

  SampleResult add_twist(
    int64_t stamp_ns, const FirmwareTwist & twist, int64_t ros_now_ns, int64_t steady_now_ns)
  {
    advance(ros_now_ns, steady_now_ns);
    if (!valid_twist(twist)) {
      return {SampleStatus::Invalid, std::nullopt};
    }
    const auto status = stamp_status(stamp_ns, ros_now_ns);
    if (status != SampleStatus::Waiting) {
      return {status, std::nullopt};
    }
    auto & pair = get_pair(stamp_ns, steady_now_ns);
    if (pair.twist) {
      return {SampleStatus::Duplicate, std::nullopt};
    }
    pair.twist = twist;
    return finish(stamp_ns);
  }

  std::size_t pending_size() const {return pending_.size();}

  static bool valid_pose(const FirmwarePose & pose)
  {
    if (!finite(pose.position) || !finite(pose.orientation)) {
      return false;
    }
    const auto & q = pose.orientation;
    const double norm2 = q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3];
    return std::abs(norm2 - 1.0) <= 1e-3 &&
           std::abs(pose.position[2]) <= 1e-6 &&
           std::abs(q[0]) <= 1e-6 && std::abs(q[1]) <= 1e-6;
  }

  static bool valid_twist(const FirmwareTwist & twist)
  {
    return finite(twist.linear) && finite(twist.angular) &&
           std::abs(twist.linear[1]) <= 1e-6 && std::abs(twist.linear[2]) <= 1e-6 &&
           std::abs(twist.angular[0]) <= 1e-6 && std::abs(twist.angular[1]) <= 1e-6;
  }

private:
  struct Pair
  {
    int64_t first_receipt_ns;
    std::optional<FirmwarePose> pose;
    std::optional<FirmwareTwist> twist;
  };

  template<std::size_t N>
  static bool finite(const std::array<double, N> & values)
  {
    for (const double value : values) {
      if (!std::isfinite(value)) {
        return false;
      }
    }
    return true;
  }

  SampleStatus stamp_status(int64_t stamp_ns, int64_t ros_now_ns) const
  {
    if (stamp_ns <= 0 || ros_now_ns <= 0) {
      return SampleStatus::Invalid;
    }
    if (ros_now_ns - stamp_ns > config_.max_sample_age_ns) {
      return SampleStatus::Stale;
    }
    if (stamp_ns - ros_now_ns > config_.future_tolerance_ns) {
      return SampleStatus::Future;
    }
    if (last_published_ns_ && stamp_ns <= *last_published_ns_) {
      return SampleStatus::Duplicate;
    }
    return SampleStatus::Waiting;
  }

  Pair & get_pair(int64_t stamp_ns, int64_t steady_now_ns)
  {
    auto it = pending_.find(stamp_ns);
    if (it == pending_.end()) {
      // Bound memory even if only one topic keeps arriving.
      if (pending_.size() >= config_.queue_size) {
        pending_.erase(pending_.begin());
      }
      it = pending_.emplace(stamp_ns, Pair{steady_now_ns, {}, {}}).first;
    }
    return it->second;
  }

  SampleResult finish(int64_t stamp_ns)
  {
    const auto & pair = pending_.at(stamp_ns);
    if (!pair.pose || !pair.twist) {
      return {SampleStatus::Waiting, std::nullopt};
    }
    FirmwareSample sample{stamp_ns, *pair.pose, *pair.twist};
    auto & q = sample.pose.orientation;
    const double norm = std::sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
    for (double & value : q) {
      value /= norm;
    }
    last_published_ns_ = stamp_ns;
    // Late pairs can never produce backward odom/TF within a clock epoch.
    pending_.erase(pending_.begin(), pending_.upper_bound(stamp_ns));
    return {SampleStatus::Published, sample};
  }

  SynchronizerConfig config_;
  std::map<int64_t, Pair> pending_;
  std::optional<int64_t> last_published_ns_;
  std::optional<int64_t> last_ros_now_ns_;
};

}  // namespace megarover3_bringup
#endif  // MEGAROVER3_BRINGUP__FIRMWARE_ODOMETRY_HPP_
