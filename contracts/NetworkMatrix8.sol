// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @dev OpenZeppelin Contracts (IERC20 & ReentrancyGuard interfaces)
 */
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function decimals() external view returns (uint8);
}

/**
 * @title NetworkMatrix8
 * @dev Decentralized 8-Level Web3 Network Marketing System with Instant Payouts
 * Registration Fee: 3.4 USDT
 * Level 1: 21% (0.714 USDT)
 * Level 2: 16% (0.544 USDT)
 * Level 3: 13% (0.442 USDT)
 * Level 4:  9% (0.306 USDT)
 * Level 5:  6% (0.204 USDT)
 * Level 6:  3% (0.102 USDT)
 * Level 7:  2% (0.068 USDT)
 * Level 8:  1% (0.034 USDT)
 * Total Upline Commission = 71% (2.414 USDT)
 * System Treasury Base = 29% (0.986 USDT)
 * Any missing / orphaned levels in the 8-tier chain automatically route to System Treasury.
 */
contract NetworkMatrix8 {
    // ----------------------------------------------------
    // CONSTANTS & CONFIGURATION
    // ----------------------------------------------------
    uint256 public constant REGISTRATION_FEE_USDT_UNITS = 3400000; // 3.4 USDT (assuming 6 decimals) or scaled dynamically
    uint256 public constant COMMISSION_DENOMINATOR = 10000; // 100% = 10000 bps

    // 8-Level Commission distribution in basis points (100 bps = 1%)
    uint16[8] public LEVEL_PERCENTAGES = [
        2100, // Level 1: 21%
        1600, // Level 2: 16%
        1300, // Level 3: 13%
        900,  // Level 4: 9%
        600,  // Level 5: 6%
        300,  // Level 6: 3%
        200,  // Level 7: 2%
        100   // Level 8: 1%
    ];

    uint16 public constant SYSTEM_BASE_PERCENTAGE = 2900; // 29% Base System Account

    IERC20 public immutable usdtToken;
    address public systemTreasury;
    address public owner;

    uint256 public totalUsers;
    uint256 public totalVolumeDistributed;
    uint256 public totalSystemCollected;

    // ----------------------------------------------------
    // STRUCTS & MAPPINGS
    // ----------------------------------------------------
    struct User {
        uint256 uniqueId;
        address walletAddress;
        address referrer;
        uint256 joinTimestamp;
        bool isRegistered;
        uint256 totalEarned;
        uint256[8] levelMemberCount;
        uint256[8] levelEarnings;
    }

    mapping(address => User) public users;
    mapping(uint256 => address) public idToAddress;
    mapping(address => uint256) public addressToId;

    // Direct downlines list
    mapping(address => address[]) private directReferrals;

    // Reentrancy lock
    uint256 private _status;
    modifier nonReentrant() {
        require(_status != 2, "ReentrancyGuard: reentrant call");
        _status = 2;
        _;
        _status = 1;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can invoke this");
        _;
    }

    // ----------------------------------------------------
    // EVENTS
    // ----------------------------------------------------
    event UserRegistered(
        address indexed user,
        uint256 indexed uniqueId,
        address indexed referrer,
        uint256 timestamp
    );

    event CommissionDistributed(
        address indexed payer,
        address indexed receiver,
        uint8 indexed level,
        uint256 amount,
        uint256 timestamp
    );

    event SystemFeeCollected(
        address indexed payer,
        uint256 baseFeeAmount,
        uint256 orphanedLevelsAmount,
        uint256 totalAmount,
        uint256 timestamp
    );

    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);

    // ----------------------------------------------------
    // CONSTRUCTOR
    // ----------------------------------------------------
    constructor(address _usdtTokenAddress, address _systemTreasury) {
        require(_usdtTokenAddress != address(0), "Invalid token address");
        require(_systemTreasury != address(0), "Invalid treasury address");
        
        usdtToken = IERC20(_usdtTokenAddress);
        systemTreasury = _systemTreasury;
        owner = msg.sender;
        _status = 1;

        // Register Genesis Root (ID: 100001)
        totalUsers = 1;
        uint256 rootId = 100001;
        users[_systemTreasury].uniqueId = rootId;
        users[_systemTreasury].walletAddress = _systemTreasury;
        users[_systemTreasury].referrer = address(0);
        users[_systemTreasury].joinTimestamp = block.timestamp;
        users[_systemTreasury].isRegistered = true;

        idToAddress[rootId] = _systemTreasury;
        addressToId[_systemTreasury] = rootId;

        emit UserRegistered(_systemTreasury, rootId, address(0), block.timestamp);
    }

    // ----------------------------------------------------
    // REGISTRATION & COMMISSION DISTRIBUTION
    // ----------------------------------------------------
    /**
     * @notice Register a new member into the 8-level matrix
     * @param referrerAddress Address of the sponsor (or system treasury if none)
     */
    function register(address referrerAddress) external nonReentrant {
        address newUser = msg.sender;
        require(!users[newUser].isRegistered, "User already registered");
        
        if (referrerAddress == address(0) || !users[referrerAddress].isRegistered || referrerAddress == newUser) {
            referrerAddress = systemTreasury;
        }

        // Calculate registration fee adjusted to token decimals
        uint8 decimals = usdtToken.decimals();
        uint256 fee = 34 * (10 ** decimals) / 10; // 3.4 USDT

        // Pull 3.4 USDT from user
        require(
            usdtToken.transferFrom(newUser, address(this), fee),
            "USDT transfer failed. Check allowance & balance."
        );

        // Assign Unique ID
        totalUsers++;
        uint256 newId = 100000 + totalUsers;

        User storage user = users[newUser];
        user.uniqueId = newId;
        user.walletAddress = newUser;
        user.referrer = referrerAddress;
        user.joinTimestamp = block.timestamp;
        user.isRegistered = true;

        idToAddress[newId] = newUser;
        addressToId[newUser] = newId;
        directReferrals[referrerAddress].push(newUser);

        emit UserRegistered(newUser, newId, referrerAddress, block.timestamp);

        // Execute 8-tier payout & system treasury routing
        _distributeCommissions(newUser, referrerAddress, fee);
    }

    /**
     * @notice Distributes commissions across up to 8 levels and routes unallocated percentages to system treasury
     */
    function _distributeCommissions(address payer, address startUpline, uint256 totalFee) internal {
        address currentUpline = startUpline;
        uint256 totalDistributedToUplines = 0;
        uint256 orphanedPercentage = 0;

        for (uint8 level = 0; level < 8; level++) {
            uint16 percentage = LEVEL_PERCENTAGES[level];
            uint256 commissionAmount = (totalFee * percentage) / COMMISSION_DENOMINATOR;

            if (currentUpline != address(0) && users[currentUpline].isRegistered && currentUpline != systemTreasury) {
                // Transfer commission directly to upline's wallet
                users[currentUpline].totalEarned += commissionAmount;
                users[currentUpline].levelMemberCount[level] += 1;
                users[currentUpline].levelEarnings[level] += commissionAmount;

                totalDistributedToUplines += commissionAmount;

                require(
                    usdtToken.transfer(currentUpline, commissionAmount),
                    "Commission transfer failed"
                );

                emit CommissionDistributed(payer, currentUpline, level + 1, commissionAmount, block.timestamp);

                // Move up the chain
                currentUpline = users[currentUpline].referrer;
            } else {
                // If chain is broken or reached root/zero, route this level percentage to system
                orphanedPercentage += percentage;
                if (currentUpline != address(0)) {
                    currentUpline = users[currentUpline].referrer;
                }
            }
        }

        // Calculate System Treasury share: 29% Base + Orphaned levels
        uint256 baseSystemFee = (totalFee * SYSTEM_BASE_PERCENTAGE) / COMMISSION_DENOMINATOR;
        uint256 orphanedAmount = (totalFee * orphanedPercentage) / COMMISSION_DENOMINATOR;
        uint256 totalSystemAmount = baseSystemFee + orphanedAmount;

        totalSystemCollected += totalSystemAmount;
        totalVolumeDistributed += totalFee;

        // Route System Amount to System Treasury Wallet
        if (totalSystemAmount > 0) {
            require(
                usdtToken.transfer(systemTreasury, totalSystemAmount),
                "System Treasury transfer failed"
            );

            emit SystemFeeCollected(payer, baseSystemFee, orphanedAmount, totalSystemAmount, block.timestamp);
        }
    }

    // ----------------------------------------------------
    // GETTERS & ANALYTICS
    // ----------------------------------------------------
    function getUserLevelStats(address userAddress) external view returns (
        uint256[8] memory memberCounts,
        uint256[8] memory levelEarnings
    ) {
        return (users[userAddress].levelMemberCount, users[userAddress].levelEarnings);
    }

    function getDirectReferrals(address userAddress) external view returns (address[] memory) {
        return directReferrals[userAddress];
    }

    function setSystemTreasury(address _newTreasury) external onlyOwner {
        require(_newTreasury != address(0), "Invalid address");
        address oldTreasury = systemTreasury;
        systemTreasury = _newTreasury;
        emit TreasuryUpdated(oldTreasury, _newTreasury);
    }
}
