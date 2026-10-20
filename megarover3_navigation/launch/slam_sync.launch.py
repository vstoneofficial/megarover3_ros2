import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share = get_package_share_directory('megarover3_navigation')
    return LaunchDescription([
        DeclareLaunchArgument(
            'rvizconfig', default_value=os.path.join(share, 'rviz', 'slam.rviz'),
        ),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument(
            'use_lifecycle_manager', default_value='false',
            description='External manager owns transitions; disables launch autostart.',
        ),
        DeclareLaunchArgument(
            'use_sim_time', default_value='false',
            description='Use /clock for simulation or replay; false uses system time.',
        ),
        DeclareLaunchArgument(
            'slam_params_file',
            default_value=os.path.join(share, 'config', 'mapper_params_online_sync.yaml'),
        ),
        Node(
            condition=IfCondition(LaunchConfiguration('use_rviz')),
            package='rviz2', executable='rviz2', name='rviz2', output='screen',
            parameters=[{
                'use_sim_time': ParameterValue(
                    LaunchConfiguration('use_sim_time'), value_type=bool,
                ),
            }],
            arguments=['-d', LaunchConfiguration('rvizconfig')],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                share, 'launch', 'internal', 'slam_sync_internal.launch.py',
            )),
            launch_arguments={
                name: LaunchConfiguration(name) for name in (
                    'autostart', 'use_lifecycle_manager', 'use_sim_time', 'slam_params_file',
                )
            }.items(),
        ),
    ])
