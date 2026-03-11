from ament_index_python.packages import get_package_share_path
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch_ros.substitutions import FindPackageShare
from launch import LaunchDescription
from launch.substitutions import PathJoinSubstitution, LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    rviz_config_path = get_package_share_path('megarover3_navigation') / 'rviz/slam.rviz'

    rover_arg = DeclareLaunchArgument(
        name='rover',
        default_value='mega3',
        description='Rover type: mega3, f120a, s40a_lb'
    )

    rviz_arg = DeclareLaunchArgument(
        name='rvizconfig',
        default_value=str(rviz_config_path),
        description='Absolute path to rviz config file'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
    )

    launch_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('megarover3_navigation'),
                'launch',
                'internal/slam_async.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': 'false',
        }.items()
    )

    return LaunchDescription([
        rover_arg,
        rviz_arg,
        rviz_node,
        launch_slam,
    ])
