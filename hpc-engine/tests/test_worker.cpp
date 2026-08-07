#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <chrono>
#include <cassert>

#include <grpcpp/grpcpp.h>
#include "pipeline.grpc.pb.h"
#include "worker_server.hpp"

// Funzione helper per avviare il server in un thread separato
void start_test_server(const std::string& address) {
    RunServer(address, "test-worker");
}

int main() {
    std::string server_address("0.0.0.0:50052");
    
    // 1. Avvia il server in un thread
    std::thread server_thread(start_test_server, server_address);
    std::this_thread::sleep_for(std::chrono::milliseconds(500)); // Attendi avvio server
    
    // 2. Crea il client stub
    auto channel = grpc::CreateChannel(server_address, grpc::InsecureChannelCredentials());
    std::unique_ptr<pipeline::PipelineWorker::Stub> stub = pipeline::PipelineWorker::NewStub(channel);
    
    std::cout << "Testing Ping..." << std::endl;
    {
        grpc::ClientContext context;
        google::protobuf::Empty request;
        pipeline::Status response;
        grpc::Status status = stub->Ping(&context, request, &response);
        assert(status.ok() && "Ping failed");
        assert(response.healthy() && "Ping response not healthy");
        assert(response.node_id() == "test-worker" && "Incorrect node id");
    }
    
    std::cout << "Testing ExecuteTask (INCREMENT_COUNTER)..." << std::endl;
    {
        grpc::ClientContext context;
        pipeline::TaskRequest request;
        request.set_operation(pipeline::INCREMENT_COUNTER);
        request.set_input_value(42);
        request.set_pipeline_id("test-pipeline");
        
        pipeline::TaskResult response;
        grpc::Status status = stub->ExecuteTask(&context, request, &response);
        assert(status.ok() && "ExecuteTask failed");
        assert(response.output_value() == 43 && "Value not incremented correctly");
        assert(response.node_id() == "test-worker" && "Incorrect node id");
    }
    
    std::cout << "Testing ExecuteTask (OPERATION_UNKNOWN)..." << std::endl;
    {
        grpc::ClientContext context;
        pipeline::TaskRequest request;
        request.set_operation(pipeline::OPERATION_UNKNOWN);
        request.set_input_value(42);
        request.set_pipeline_id("test-pipeline");
        
        pipeline::TaskResult response;
        grpc::Status status = stub->ExecuteTask(&context, request, &response);
        // Deve restituire errore UNIMPLEMENTED
        assert(!status.ok() && "ExecuteTask should have failed");
        assert(status.error_code() == grpc::StatusCode::UNIMPLEMENTED && "Incorrect error code");
    }
    
    std::cout << "All gRPC worker tests passed!" << std::endl;
    
    // Nota: grpc server in RunServer è bloccante, per terminare in modo pulito 
    // potremmo gestire uno shutdown, ma per un test isolato std::exit(0) va bene.
    std::exit(0);
}
