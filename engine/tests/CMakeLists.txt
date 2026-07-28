add_executable(
    chinese_durak_engine_tests
    test_game_engine.cpp
)

target_link_libraries(
    chinese_durak_engine_tests
    PRIVATE
    chinese_durak_engine
)

target_compile_features(
    chinese_durak_engine_tests
    PRIVATE
    cxx_std_20
)

if(MSVC)
    target_compile_options(
        chinese_durak_engine_tests
        PRIVATE
        /W4
        /permissive-
    )
else()
    target_compile_options(
        chinese_durak_engine_tests
        PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Wconversion
    )
endif()

add_test(
    NAME chinese_durak_engine_tests
    COMMAND chinese_durak_engine_tests
)
