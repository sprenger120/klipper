cmake_minimum_required(VERSION 3.10)
project(c_helper C CXX)

set(CMAKE_CXX_STANDARD 23)
if (CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
endif ()

# c_helper.so
add_library(${PROJECT_NAME} SHARED
        itersolve.c
        kin_cartesian.c
        #kin_corexy.c
        #kin_corexz.c
        #kin_delta.c
        #kin_deltesian.c
        #kin_extruder.c
        #kin_idex.c
        #kin_polar.c
        #kin_rotary_delta.c
        #kin_shaper.c
        #kin_winch.c
        msgblock.c
        pollreactor.c
        pyhelper.c
        serialqueue.c
        stepcompress.c
        trapq.c
        trdispatch.c
)
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# test application
add_executable(${PROJECT_NAME}_test main.cpp)
target_link_libraries(${PROJECT_NAME}_test PUBLIC ${PROJECT_NAME})
