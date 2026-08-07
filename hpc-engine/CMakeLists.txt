cmake_minimum_required(VERSION 3.16)
project(hpc-engine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Aggiunto -Wall -Wextra esplicitamente come richiesto
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")

# OpenMP
find_package(OpenMP REQUIRED)

# OpenSSL
find_package(OpenSSL REQUIRED)

include_directories(${OPENSSL_INCLUDE_DIR})

# Sorgenti principali
add_executable(hpc_engine_bench
    src/onboarding/main.cpp
    src/onboarding/device_generator.cpp
    src/onboarding/signature_bench.cpp
    src/onboarding/csv_writer.cpp
)

target_link_libraries(hpc_engine_bench
    PRIVATE OpenMP::OpenMP_CXX
    PRIVATE OpenSSL::SSL
    PRIVATE OpenSSL::Crypto
)

enable_testing()
add_executable(test_signatures 
    tests/test_signatures.cpp
    src/onboarding/device_generator.cpp
)
target_include_directories(test_signatures PRIVATE src/onboarding)
target_link_libraries(test_signatures
    PRIVATE OpenSSL::SSL
    PRIVATE OpenSSL::Crypto
)
add_test(NAME SignatureCorrectness COMMAND test_signatures)

# --- gRPC per M6 ---
find_package(PkgConfig REQUIRED)
pkg_check_modules(GRPC REQUIRED grpc++)
pkg_check_modules(PROTOBUF REQUIRED protobuf)

find_program(PROTOC_EXECUTABLE protoc REQUIRED)
find_program(GRPC_CPP_PLUGIN_EXECUTABLE grpc_cpp_plugin REQUIRED)

set(PROTO_SRC "${CMAKE_CURRENT_BINARY_DIR}/pipeline.pb.cc")
set(PROTO_HEADER "${CMAKE_CURRENT_BINARY_DIR}/pipeline.pb.h")
set(GRPC_SRC "${CMAKE_CURRENT_BINARY_DIR}/pipeline.grpc.pb.cc")
set(GRPC_HEADER "${CMAKE_CURRENT_BINARY_DIR}/pipeline.grpc.pb.h")
set(PROTO_FILE "${CMAKE_SOURCE_DIR}/../proto/pipeline.proto")

add_custom_command(
    OUTPUT ${PROTO_SRC} ${PROTO_HEADER} ${GRPC_SRC} ${GRPC_HEADER}
    COMMAND ${PROTOC_EXECUTABLE}
    ARGS --grpc_out=${CMAKE_CURRENT_BINARY_DIR}
         --cpp_out=${CMAKE_CURRENT_BINARY_DIR}
         -I ${CMAKE_SOURCE_DIR}/../proto
         --plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN_EXECUTABLE}
         ${PROTO_FILE}
    DEPENDS ${PROTO_FILE}
)

add_executable(pipeline_worker
    src/pipeline/main_worker.cpp
    src/pipeline/worker_server.cpp
    ${PROTO_SRC}
    ${GRPC_SRC}
)

target_include_directories(pipeline_worker PRIVATE ${CMAKE_CURRENT_BINARY_DIR} src/pipeline)
target_link_libraries(pipeline_worker
    PRIVATE ${GRPC_LIBRARIES} ${PROTOBUF_LIBRARIES}
)

add_executable(test_worker
    tests/test_worker.cpp
    src/pipeline/worker_server.cpp
    ${PROTO_SRC}
    ${GRPC_SRC}
)
target_include_directories(test_worker PRIVATE ${CMAKE_CURRENT_BINARY_DIR} src/pipeline)
target_link_libraries(test_worker
    PRIVATE ${GRPC_LIBRARIES} ${PROTOBUF_LIBRARIES}
)
add_test(NAME WorkerCorrectness COMMAND test_worker)
