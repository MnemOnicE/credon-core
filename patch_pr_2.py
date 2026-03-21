import re

with open('contracts/src/ConvictionGovernor.sol', 'r') as f:
    content = f.read()

# Fix 1: _calculateThreshold fallback
threshold_orig = """        } catch {
            totalSupply = 1000; // Fallback if not enumerable
        }"""
threshold_new = """        } catch {
            revert("Failed to get totalSupply from CRED_TOKEN. Ensure it implements IERC721Enumerable.");
        }"""
content = content.replace(threshold_orig, threshold_new)

with open('contracts/src/ConvictionGovernor.sol', 'w') as f:
    f.write(content)
