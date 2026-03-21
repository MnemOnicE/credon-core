with open('contracts/src/ConvictionGovernor.sol', 'r') as f:
    content = f.read()

import re
print(re.search(r'function executeProposal\(uint256 proposalId\).*?\{.*?\}', content, re.DOTALL).group(0))
