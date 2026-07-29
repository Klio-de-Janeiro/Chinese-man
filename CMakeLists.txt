cmake_minimum_required(VERSION 3.25)

project(
    chinese_durak
    VERSION 0.2.4
    DESCRIPTION "Authoritative engine for Chinese Durak"
    LANGUAGES CXX
)

option(CHINESE_DURAK_BUILD_TESTS "Build native engine tests" ON)
option(CHINESE_DURAK_BUILD_PYTHON "Build Python bindings" OFF)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory(engine)

if(CHINESE_DURAK_BUILD_TESTS)
    include(CTest)
    enable_testing()
    add_subdirectory(engine/tests)
endif()

if(CHINESE_DURAK_BUILD_PYTHON)
    find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
    find_package(pybind11 CONFIG REQUIRED)
    add_subdirectory(bindings/python)
endif()
