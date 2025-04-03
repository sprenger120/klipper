cmake_minimum_required(VERSION 3.10)
project(klipper-chelper C)

file(GLOB SOURCES *.c)

add_library(${PROJECT_NAME} SHARED
    ${SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})