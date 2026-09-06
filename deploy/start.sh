#!/usr/bin/env bash
set -euo pipefail
# Launcher for the RB300 ROS2 system.
# Sources the version pointed to by the current symlink and starts the launch file.

ROS_DISTRO="${ROS_DISTRO:-humble}"
APP_ROOT="/opt/app/rb300"
CURRENT="$APP_ROOT/current"

source "/opt/ros/$ROS_DISTRO/setup.bash"
source "$CURRENT/install/setup.bash"

exec ros2 launch rb300_launch rb300_system.launch.py "$@"
