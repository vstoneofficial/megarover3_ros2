from ament_index_python.packages import get_package_share_path
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node


from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    rviz_config_path = get_package_share_path('megarover3_bringup') / 'rviz/laser.rviz'

    launch_description = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('megarover_description'),
                    'launch',
                    'mega3_view.launch.py'
                ])
            ]),
            launch_arguments={
                'rvizconfig': str(rviz_config_path),
                'gui': 'false',
            }.items()
        )

    launch_ydlidar = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('megarover3_bringup'),
                    'launch',
                    'ydlidar_tg30_launch.py'
                ])
            ]),
        )
    
    pub_odom_node = Node(
        package='megarover3_bringup',
        executable='pub_odom',
        name='pub_odom'
    )

    return LaunchDescription([
        launch_description,
        launch_ydlidar,
        pub_odom_node
    ])
