cmake_minimum_required(VERSION 3.10)
project(orca-utils NONE)

# Stage orca-scripts/ under $INSTALL/scripts/orca-scripts, .sh and .py only
install(
    DIRECTORY orca-scripts/
    DESTINATION scripts/orca-scripts
    USE_SOURCE_PERMISSIONS
    FILES_MATCHING
    PATTERN "*.sh"
    PATTERN "*.py"
)
