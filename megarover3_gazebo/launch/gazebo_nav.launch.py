#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import signal
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess,
    TimerAction,
    RegisterEventHandler,
    LogInfo
)
from launch.event_handlers import OnShutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.substitutions import FindPackageShare


def check_service(service_name, timeout=30):
    for _ in range(timeout):
        result = subprocess.run(['ros2', 'service', 'list'], capture_output=True, text=True)
        if service_name in result.stdout:
            print(f"[{service_name}] [OK]")
            return True
        time.sleep(1)
    print(f"[{service_name}] [TIMEOUT]")
    return False


def check_tf(source, target, timeout=30):
    for _ in range(timeout):
        result = subprocess.run(['ros2', 'run', 'tf2_ros', 'tf2_echo', source, target, '--once'],
                                capture_output=True, text=True)
        if 'At time' in result.stdout:
            print(f"[tf {source}->{target}] [OK]")
            return True
        time.sleep(1)
    print(f"[tf {source}->{target}] [TIMEOUT]")
    return False


def kill_gazebo():
    for proc in ("gzserver", "gzclient"):
        subprocess.run(['pkill', '-9', proc], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def generate_launch_description():
    kill_gazebo()
    print("[gazebo_cleanup] [OK]")

    # --- Launch Arguments ---
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    gui = LaunchConfiguration('gui', default='true')
    verbose = LaunchConfiguration('verbose', default='false')

    pkg_gzb = FindPackageShare('megarover3_gazebo')
    pkg_nav = FindPackageShare('megarover3_navigation')

    default_map = PathJoinSubstitution([pkg_gzb, 'maps', 'test2.yaml'])
    params_file = PathJoinSubstitution([pkg_nav, 'config', 'mega3_nav2_params.yaml'])
    
    print("[gazebo_bringup.py] --- 起動中...")
    gazebo_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_gzb, 'launch', 'gazebo_bringup.launch.py'])
        ]),
        launch_arguments={'use_sim_time': use_sim_time, 'gui': gui, 'verbose': verbose}.items()
    )

    def wait_gazebo():
        for _ in range(15):
            result = subprocess.run(['ros2', 'topic', 'list'], capture_output=True, text=True)
            if '/clock' in result.stdout:
                print("[gazebo_bringup.py] [OK]")
                return
            time.sleep(1)
        print("[gazebo_bringup.py] [TIMEOUT]")

    import threading
    threading.Thread(target=wait_gazebo, daemon=True).start()

    def wait_spawn():
        print("[spawn_wall.py] --- 起動中...")
        ok = check_service('/spawn_entity', 30)
        if ok:
            print("[spawn_wall.py] [OK]")
        else:
            print("[spawn_wall.py] [TIMEOUT]")

    spawn_wall = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_gzb, 'launch', 'spawn_wall.launch.py'])
        ]),
        launch_arguments={'use_sim_time': use_sim_time}.items()
    )

    threading.Thread(target=wait_spawn, daemon=True).start()

    def wait_tf():
        print("[tf_check] --- 確認中...")
        ok = check_tf('odom', 'base_footprint', 25)
        if not ok:
            print("[tf_check] [TIMEOUT]")

    threading.Thread(target=wait_tf, daemon=True).start()

    def delayed_nav2_start():
        print("[navigation.launch.py] --- 起動中...")
        time.sleep(10)
        print("[navigation.launch.py] [OK]")

    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([pkg_nav, 'launch', 'navigation.launch.py'])
        ]),
        launch_arguments={
            'map': default_map,
            'params_file': params_file,
            'use_sim_time': use_sim_time,
        }.items()
    )
    threading.Thread(target=delayed_nav2_start, daemon=True).start()

    nav2_timer = TimerAction(
        period=20.0,
        actions=[navigation]
    )

    cleanup = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[
                LogInfo(msg='[system] 停止処理中...'),
                ExecuteProcess(cmd=['pkill', '-9', 'gzserver'], shell=True),
                ExecuteProcess(cmd=['pkill', '-9', 'gzclient'], shell=True),
            ]
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('verbose', default_value='false'),

        gazebo_bringup,
        spawn_wall,
        nav2_timer,
        cleanup
    ])

