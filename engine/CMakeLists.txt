add_library(
    chinese_durak_engine
    STATIC
    src/card.cpp
    src/game_engine.cpp
)

target_include_directories(
    chinese_durak_engine
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(chinese_durak_engine PUBLIC cxx_std_20)
set_target_properties(
    chinese_durak_engine
    PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

if(MSVC)
    target_compile_options(
        chinese_durak_engine
        PRIVATE
        /W4
        /permissive-
    )
else()
    target_compile_options(
        chinese_durak_engine
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Wconversion
    )
endif()
