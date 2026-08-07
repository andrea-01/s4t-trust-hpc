#pragma once

#include <string>
#include <grpcpp/grpcpp.h>
#include "pipeline.grpc.pb.h"

class PipelineWorkerServiceImpl final : public pipeline::PipelineWorker::Service {
public:
    PipelineWorkerServiceImpl(const std::string& node_id);

    grpc::Status Ping(grpc::ServerContext* context, const google::protobuf::Empty* request, pipeline::Status* response) override;
    
    grpc::Status ExecuteTask(grpc::ServerContext* context, const pipeline::TaskRequest* request, pipeline::TaskResult* response) override;

private:
    std::string node_id_;
};

void RunServer(const std::string& address, const std::string& node_id);
