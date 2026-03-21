with open('contracts/test/ConvictionGovernor.t.sol', 'r') as f:
    content = f.read()

import re
print(re.search(r'function test_ExecuteProposal_Success\(\).*?\{.*?\}', content, re.DOTALL).group(0))
