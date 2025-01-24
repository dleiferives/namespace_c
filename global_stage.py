import re

def stage3_extract_global_variables(code):
    # Updated regex to capture global variables with better handling of complex types
    global_var_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])*\s*(=\s*[^;]+)?;"

    # List to store global variables metadata
    global_variables = []

    # Split code into lines to exclude variables inside functions or structs
    lines = code.splitlines()
    in_function_or_struct = False

    for line in lines:
        # Check for function or struct start
        if re.search(r"\{", line):  
            in_function_or_struct = True

        # Check for function or struct end
        if re.search(r"\}", line):
            in_function_or_struct = False
            continue

        if not in_function_or_struct:
            # Match global variable declarations
            match = re.search(global_var_pattern, line.strip())
            if match:
                const = match.group(1).strip() if match.group(1) else ""
                unsigned = match.group(2).strip() if match.group(2) else ""
                var_type = match.group(3).strip()
                pointer = match.group(4).strip() if match.group(4) else ""
                var_name = match.group(5).strip()
                array = match.group(6).strip() if match.group(6) else ""
                var_value = match.group(7).strip() if match.group(7) else None
                global_variables.append({
                    "type": f"{const} {unsigned} {var_type} {pointer}".strip(),
                    "name": var_name,
                    "array": array,
                    "value": var_value
                })

    return global_variables

# Example Input
input_code = """
#include <stdio.h>

int globalVar = 42;
float globalFloat;
char *globalString = "Hello, World!";
const unsigned int globalArray[10] = {0};
double *globalPointer;

struct MyType {
    int x;
};

void myFunction() {
    int localVar = 10;
}
"""

# Extract Global Variables
global_variables = stage3_extract_global_variables(input_code)

# Print Metadata
import pprint
pprint.pprint(global_variables)
