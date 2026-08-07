#include <cassert>
#include <iostream>
#include "device_generator.hpp"
#include <openssl/err.h>

bool verify_signature(const Device& dev) {
    EVP_MD_CTX_ptr mdctx(EVP_MD_CTX_new());
    if (!mdctx) return false;
    if (EVP_DigestVerifyInit(mdctx.get(), nullptr, EVP_sha256(), nullptr, dev.keypair.get()) <= 0) return false;
    return EVP_DigestVerify(mdctx.get(), dev.signature.data(), dev.signature.size(), dev.message.data(), dev.message.size()) == 1;
}

int main() {
    std::cout << "Generating test device...\n";
    auto devices = DeviceGenerator::generate_devices(1, 12345);
    assert(devices.size() == 1);
    
    Device& dev = devices[0];
    
    std::cout << "Test 1: Verify valid signature\n";
    assert(verify_signature(dev) == true);
    
    std::cout << "Test 2: Verify tampered message\n";
    dev.message[0] ^= 0x01; // flip a bit
    assert(verify_signature(dev) == false);
    dev.message[0] ^= 0x01; // restore
    
    std::cout << "Test 3: Verify tampered signature\n";
    dev.signature[0] ^= 0x01; // flip a bit
    assert(verify_signature(dev) == false);
    dev.signature[0] ^= 0x01; // restore
    
    std::cout << "All tests passed successfully!\n";
    return 0;
}
