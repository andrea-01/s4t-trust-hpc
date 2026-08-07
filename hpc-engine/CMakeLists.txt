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
)

target_link_libraries(hpc_engine_bench
    PRIVATE OpenMP::OpenMP_CXX
    PRIVATE OpenSSL::SSL
    PRIVATE OpenSSL::Crypto
)
