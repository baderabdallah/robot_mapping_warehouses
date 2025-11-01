# Devcontainer for ROS 2 Humble on Ubuntu 22.04 (Jammy)
# Uses the official ROS base image to minimize setup friction
FROM ros:humble-ros-base

# Allow overriding ROS_DISTRO at build time and set a default value so
# references to $ROS_DISTRO during build don't expand to an empty string.
ARG ROS_DISTRO=humble
ENV ROS_DISTRO=${ROS_DISTRO}

SHELL ["/bin/bash", "-c"]

# Avoid interactive prompts during package installs
ENV DEBIAN_FRONTEND=noninteractive

# Basic tooling + ROS dev tools
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    locales \
    bash-completion \
    iputils-ping \
    net-tools \
    ca-certificates \
    python3-pip \
    python3-vcstool \
    python3-colcon-common-extensions \
    python3-rosdep \
    openjdk-11-jdk \
 && rm -rf /var/lib/apt/lists/*

# Bazel installation skipped in this devcontainer build to avoid
# architecture/repository mismatches during image build. If you need
# Bazel inside the container, install it at runtime or add a platform-
# specific installation step (for example, using bazelisk or a released
# deb matching the build architecture).

# Locale
RUN locale-gen en_US.UTF-8 && update-locale LANG=en_US.UTF-8
ENV LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8

# Initialize rosdep (root required). Ignore if already initialized.
RUN rosdep init || echo "rosdep already initialized"

# Helpful defaults in shells
# - Ensure ROS is sourced (entrypoint does this for bash shells)
# - Source workspace overlay if it exists
# - Enable colcon argcomplete if available
RUN echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> /etc/bash.bashrc \
 && echo "if [ -f /workspaces/WareHouseRobotMapping/install/local_setup.bash ]; then source /workspaces/WareHouseRobotMapping/install/local_setup.bash; fi" >> /etc/bash.bashrc \
 && if [ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash ]; then echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> /etc/bash.bashrc; fi

# Keep upstream entrypoint which sources ROS
ENV BAZELISK_BAZEL_VERSION=7.5.0

RUN ARCH="$(uname -m)" \
 && if [ "$ARCH" = "x86_64" ]; then ASSET="bazelisk-linux-amd64"; \
     elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then ASSET="bazelisk-linux-arm64"; \
     else ASSET="bazelisk-linux-amd64"; fi \
 && echo "Downloading bazelisk (will drive Bazel $BAZELISK_BAZEL_VERSION)..." \
 && curl -fsSL -o /usr/local/bin/bazel "https://github.com/bazelbuild/bazelisk/releases/latest/download/$ASSET" \
 && chmod +x /usr/local/bin/bazel

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
