^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package megarover3_bringup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Forthcoming
-----------
* Use matching firmware PoseStamped/TwistStamped samples for odometry and TF.
* Require base_footprint for firmware TwistStamped input with firmware 30.11.0.
* Reject stale or invalid planar samples and reset matching after a backward clock jump.
* Support Mega3 and F120A in the hardware launch files, with Mega3 as the default.
* Allow TG30 port overrides and preserve custom parameter-file ports by default.
* Display TG30 scans in RViz and provide configurable initial odometry covariances.
* Contributors: Matsuyama, Yoshida

1.2.0 (2025-09-24)
------------------
* Add RealSense option support and TG30 samples.
* Contributors: Matsuyama, Yoshida, jie-2204

1.1.0 (2024-03-29)
------------------
* Add F120A and TG30 samples.
* Contributors: Matsuyama

1.0.0 (2023-07-03)
------------------
* Initial commit
* Contributors: jie-2204
