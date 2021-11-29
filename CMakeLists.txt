cmake_minimum_required(VERSION 3.0.2)
project(fk-for-stewart-platform-ros)

find_package(catkin REQUIRED)

catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES test
#  CATKIN_DEPENDS other_catkin_pkg
#  DEPENDS system_lib
)

include_directories(
# include
# ${catkin_INCLUDE_DIRS}
)

catkin_install_python(PROGRAMS fk.py configuration.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)