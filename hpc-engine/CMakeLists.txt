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
