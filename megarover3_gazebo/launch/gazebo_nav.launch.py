from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, TimerAction
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    # --------------------------------------------------
    # Launch arguments
    # --------------------------------------------------
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui          = LaunchConfiguration('gui', default='true')
    verbose      = LaunchConfiguration('verbose', default='false')
    rover        = LaunchConfiguration('rover', default='mega3')
    map_file     = LaunchConfiguration('map')
    wall         = LaunchConfiguration('wall')

    # --------------------------------------------------
    # Package shares
    # --------------------------------------------------
    gazebo_pkg = FindPackageShare('megarover3_gazebo')
    nav_pkg    = FindPackageShare('megarover3_navigation')

    # --------------------------------------------------
    # Default map (FULL PATH)
    # --------------------------------------------------
    default_map = PathJoinSubstitution([
        nav_pkg,
        'maps',
        'test.yaml'
    ])

    # --------------------------------------------------
    # Gazebo bringup (robot + world)
    # --------------------------------------------------
    gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                gazebo_pkg,
                'launch',
                'gazebo_bringup.launch.py'
            ])
        ),
        launch_arguments={
            'gui': gui,
            'verbose': verbose,
            'rover': rover,
        }.items()
    )

    # --------------------------------------------------
    # Wall spawn (static object)
    # --------------------------------------------------
    spawn_wall = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                gazebo_pkg,
                'launch',
                'spawn_wall.launch.py'
            ])
        ),
        launch_arguments={
            'wall': wall,
        }.items()
    )

    # --------------------------------------------------
    # Navigation (Nav2)
    # --------------------------------------------------
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                nav_pkg,
                'launch',
                'navigation.launch.py'
            ])
        ),
        launch_arguments={
            'rover': rover,
            'map': map_file,
            'params_file': '',
            'use_sim_time': use_sim_time,
        }.items()
    )

    # Gazebo起動を優先し、RViz/Nav2を後段で起動する。
    delayed_spawn_wall = TimerAction(
        period=3.0,
        actions=[spawn_wall],
    )
    delayed_navigation = TimerAction(
        period=8.0,
        actions=[
            LogInfo(msg='[gazebo_nav] Gazebo ready. Start RViz/Nav2'),
            navigation,
        ],
    )

    # --------------------------------------------------
    # Launch description
    # --------------------------------------------------
    return LaunchDescription([

        DeclareLaunchArgument(
            'rover',
            default_value='mega3',
            description='Rover type: mega3 , f120a , s40a_lb'
        ),

        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true'
        ),

        DeclareLaunchArgument(
            'gui',
            default_value='true'
        ),

        DeclareLaunchArgument(
            'verbose',
            default_value='false'
        ),

        DeclareLaunchArgument(
            'map',
            default_value=default_map,
            description='Full path to map yaml'
        ),

        DeclareLaunchArgument(
            'wall',
            default_value='',
            description='Wall STL filename (e.g. Wall.stl, Wall2.stl)'
        ),

        gazebo_bringup,
        delayed_spawn_wall,
        delayed_navigation,
    ])
