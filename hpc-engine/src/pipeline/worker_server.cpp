#include "worker_server.hpp"
#include <iostream>
#include <chrono>

PipelineWorkerServiceImpl::PipelineWorkerServiceImpl(const std::string& node_id)
    : node_id_(node_id) {}

grpc::Status PipelineWorkerServiceImpl::Ping(grpc::ServerContext* /*context*/, const google::protobuf::Empty* /*request*/, pipeline::Status* response) {
    response->set_healthy(true);
    response->set_node_id(node_id_);
    return grpc::Status::OK;
}

grpc::Status PipelineWorkerServiceImpl::ExecuteTask(grpc::ServerContext* /*context*/, const pipeline::TaskRequest* request, pipeline::TaskResult* response) {
    if (request->operation() == pipeline::INCREMENT_COUNTER) {
        std::cout << "[" << node_id_ << "] Executing INCREMENT_COUNTER for pipeline " << request->pipeline_id() << "\n";
        response->set_output_value(request->input_value() + 1);
        response->set_node_id(node_id_);
        
        auto now = std::chrono::system_clock::now();
        std::time_t now_c = std::chrono::system_clock::to_time_t(now);
        char buf[100];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&now_c));
        response->set_timestamp(buf);
        
        return grpc::Status::OK;
    }
    
    // Explicitly handle unknown operations as requested by the user
    return grpc::Status(grpc::StatusCode::UNIMPLEMENTED, "Operation not recognized or unimplemented");
}

void RunServer(const std::string& address, const std::string& node_id) {
    PipelineWorkerServiceImpl service(node_id);
    grpc::ServerBuilder builder;
    builder.AddListeningPort(address, grpc::InsecureServerCredentials());
    builder.RegisterService(&service);
    std::unique_ptr<grpc::Server> server(builder.BuildAndStart());
    std::cout << "Worker " << node_id << " listening on " << address << std::endl;
    server->Wait();
}
