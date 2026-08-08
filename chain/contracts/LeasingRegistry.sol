// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

interface IOnboardingTrust {
    enum Status { Pending, Approved, Rejected, Revoked }
    function getDeviceStatus(string calldata deviceId) external view returns (Status);
}

/**
 * @title LeasingRegistry
 * @dev Registry of authorization for HPC worker leasing.
 */
contract LeasingRegistry {
    IOnboardingTrust public immutable onboardingTrust;

    struct LeaseInfo {
        bool isLeased;
        address leasedBy;
    }

    mapping(string => LeaseInfo) public leases;

    event NodeLeased(string indexed deviceId, address indexed leaser);
    event NodeReleased(string indexed deviceId, address indexed leaser);

    constructor(address _onboardingTrust) {
        require(_onboardingTrust != address(0), "Invalid trust contract address");
        onboardingTrust = IOnboardingTrust(_onboardingTrust);
    }

    /**
     * @dev Lease a node. The node must be Approved in the OnboardingTrust contract.
     * @param deviceId Identifier of the node.
     */
    function leaseNode(string calldata deviceId) external {
        require(!leases[deviceId].isLeased, "Node already leased");
        
        IOnboardingTrust.Status status = onboardingTrust.getDeviceStatus(deviceId);
        require(status == IOnboardingTrust.Status.Approved, "Node not approved");

        leases[deviceId] = LeaseInfo({
            isLeased: true,
            leasedBy: msg.sender
        });

        emit NodeLeased(deviceId, msg.sender);
    }

    /**
     * @dev Release a leased node. Only the current leaser can release it.
     * @param deviceId Identifier of the node.
     */
    function releaseNode(string calldata deviceId) external {
        require(leases[deviceId].isLeased, "Node not leased");
        require(leases[deviceId].leasedBy == msg.sender, "Not the current leaser");

        leases[deviceId].isLeased = false;
        leases[deviceId].leasedBy = address(0);

        emit NodeReleased(deviceId, msg.sender);
    }
}
