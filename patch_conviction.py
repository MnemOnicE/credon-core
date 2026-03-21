import re

with open('contracts/src/ConvictionGovernor.sol', 'r') as f:
    content = f.read()

# Fix naming conventions for foundry linter
content = content.replace('IERC5192 public immutable credToken;', 'IERC5192 public immutable CRED_TOKEN;')
content = content.replace('RewardsReservoir public immutable reservoir;', 'RewardsReservoir public immutable RESERVOIR;')
content = content.replace('credToken = IERC5192(_credToken);', 'CRED_TOKEN = IERC5192(_credToken);')
content = content.replace('reservoir = RewardsReservoir(_reservoir);', 'RESERVOIR = RewardsReservoir(_reservoir);')
content = content.replace('address(credToken)', 'address(CRED_TOKEN)')
content = content.replace('address(reservoir)', 'address(RESERVOIR)')

content = content.replace('uint256 public currentVBE;', 'uint256 public currentVbe;')
content = content.replace('currentVBE = WAD;', 'currentVbe = WAD;')
content = content.replace('currentVBE = newVbe;', 'currentVbe = newVbe;')
content = content.replace('currentVBE < VBE_BASE_THRESHOLD', 'currentVbe < VBE_BASE_THRESHOLD')

content = content.replace('event VBEUpdated(uint256 newVBE);', 'event VbeUpdated(uint256 newVbe);')
content = content.replace('emit VBEUpdated(newVBE);', 'emit VbeUpdated(newVbe);')

content = content.replace('updateVBE(uint256 newVBE)', 'updateVbe(uint256 newVbe)')

content = content.replace('_getVBEAdjustedParameters()', '_getVbeAdjustedParameters()')

with open('contracts/src/ConvictionGovernor.sol', 'w') as f:
    f.write(content)
