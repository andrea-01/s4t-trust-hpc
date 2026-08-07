#include "worker_server.hpp"
#include <iostream>
#include <cstdlib>
#include <string>

int main(int argc, char** argv) {
    std::string port = "50051";
    if (const char* env_port = std::getenv("PORT")) {
        port = env_port;
    }
    
    std::string node_id = "worker-default";
    if (const char* env_node_id = std::getenv("NODE_ID")) {
        node_id = env_node_id;
    }
    
    std::string server_address("0.0.0.0:" + port);
    RunServer(server_address, node_id);
    
    return 0;
}
