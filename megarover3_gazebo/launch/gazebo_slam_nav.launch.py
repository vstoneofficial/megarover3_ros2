import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction, SetLaunchConfiguration, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def _auto_disable_gazebo_gui_when_headless(context, *args, **kwargs):
    gui = LaunchConfiguration('gui').perform(context).lower()
    has_display = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
    if (not has_display) and gui in ('true', '1', 'yes', 'on'):
        return [
            LogInfo(msg='[gazebo_slam_nav] 表示環境がないため Gazebo GUI を無効化します。'),
            SetLaunchConfiguration('gui', 'false'),
        ]
    return []


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    gui = LaunchConfiguration('gui')
    rover = LaunchConfiguration('rover')
    wall = LaunchConfiguration('wall')
    rviz_config = LaunchConfiguration('rvizconfig')
    physics = LaunchConfiguration('physics')

    gazebo_pkg = FindPackageShare('megarover3_gazebo')
    nav_pkg = FindPackageShare('megarover3_navigation')

    map_file = PathJoinSubstitution([nav_pkg, 'maps', 'test.yaml'])

    gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([gazebo_pkg, 'launch', 'gazebo_bringup.launch.py'])
        ),
        launch_arguments={
            'gui': gui,
            'rover': rover,
            'physics': physics,
        }.items(),
    )

    spawn_wall = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([gazebo_pkg, 'launch', 'spawn_wall.launch.py'])
        ),
        launch_arguments={
            'wall': wall,
        }.items(),
    )
    delayed_spawn_wall = TimerAction(
        period=12.0,
        actions=[spawn_wall],
    )

    slam_nav = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([nav_pkg, 'launch', 'navigation.launch.py'])
        ),
        launch_arguments={
            'rover': rover,
            'slam': 'True',
            'map': map_file,
            'use_sim_time': use_sim_time,
            'params_file': '',
            'use_rviz': 'false',
            'autostart': 'true',
            'use_composition': 'False',
            'use_respawn': 'True',
            'log_level': 'info',
        }.items(),
    )
    delayed_slam_nav = TimerAction(
        period=16.0,
        actions=[slam_nav],
    )

    # ルール: RVizは必ず表示する（Gazebo GUIのON/OFFとは独立）
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=[
            '-d', rviz_config,
            '--ros-args',
            '--log-level', 'rviz2:=fatal',
            '--log-level', 'rviz_navigation_dialog_action_client:=fatal',
        ],
        additional_env={
            'QT_QPA_PLATFORM': 'xcb',
            'LIBGL_ALWAYS_SOFTWARE': '1',
            'QT_XCB_GL_INTEGRATION': 'none',
        },
        parameters=[{'use_sim_time': use_sim_time}],
    )
    delayed_rviz = TimerAction(
        period=18.0,
        actions=[rviz_node],
    )

    return LaunchDescription([
        DeclareLaunchArgument('rover', default_value='mega3', description='Rover type: mega3, f120a, s40a_lb'),
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('wall', default_value='Wall.stl', description='Wall STL filename for static obstacle (set none to disable)'),
        DeclareLaunchArgument('physics', default_value='ode', description='Gazebo physics engine: bullet or ode'),
        DeclareLaunchArgument('rvizconfig', default_value=PathJoinSubstitution([nav_pkg, 'rviz', 'nav2.rviz']), description='RViz config file (default: nav2.rviz)'),

        LogInfo(msg='[gazebo_slam_nav] Core robot runtime nodes (robot_state_publisher, rover_twist_relay, gazebo_odom_bridge) are launched by gazebo_bringup.launch.py'),
        OpaqueFunction(function=_auto_disable_gazebo_gui_when_headless),
        gazebo_bringup,
        delayed_spawn_wall,
        delayed_slam_nav,
        delayed_rviz,
    ])
