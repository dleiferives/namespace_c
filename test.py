#!/usr/bin/env python3

import re

# Define the regular expression pattern
METHOD_PATTERN = r"((?:^[^\S\r\n]*\/\/.*\r?\n)*\s*)\s*(\w+)\s+@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};"

# Sample input
sample_input = """// this is a test comment
int @increment(int value) {
    return value + 1;
};
// this is a second test comment
int @global_increment(int value) {
    return value + MyType@y;
};"""

# Test the pattern
matches = re.finditer(METHOD_PATTERN, sample_input)

# Print the results
for match in matches:
    print("Full match:", match.group(0))
    print("Comments:", match.group(1).strip())
    print("Return type:", match.group(2))
    print("Method name:", match.group(3))
    print("Parameters:", match.group(4))
    print("Method body:", match.group(5).strip())
    print("---")
