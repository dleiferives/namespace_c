
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


def stage2_extract_functions(code):
    # Regex to match function definitions
    function_pattern = r"(\w+)\s*\(([\s\S]*?)\)\s*{([\s\S]*?)}"

    # Dictionary to store function metadata
    functions_metadata = {}

    # Find all function definitions
    functions = re.finditer(function_pattern, code)
    for function in functions:
        function_name = function.group(1)
        arguments = function.group(2).strip()
        body = function.group(3).strip()

        # Parse arguments into type and name pairs
        arguments_list = []
        for arg in arguments.split(','):
            arg = arg.strip()
            if arg:  # Ensure it's not an empty string
                arg_parts = arg.split()
                if len(arg_parts) == 2:
                    arg_type, arg_name = arg_parts
                    arguments_list.append({"type": arg_type, "name": arg_name})
                else:
                    arguments_list.append({"type": None, "name": arg_parts[0]})

        # Store function metadata
        functions_metadata[function_name] = {
            "arguments": arguments_list,
            "body": body
        }

    return functions_metadata

def extract_declarations(code):
    declaration_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])*\s*(=\s*[^;]+)?;"
    declarations = []
    lines = code.splitlines()
    for line in lines:
        match = re.search(declaration_pattern, line.strip())
        if match:
            const = match.group(1).strip() if match.group(1) else ""
            unsigned = match.group(2).strip() if match.group(2) else ""
            var_type = match.group(3).strip()
            pointer = match.group(4).strip() if match.group(4) else ""
            var_name = match.group(5).strip()
            array = match.group(6).strip() if match.group(6) else ""
            var_value = match.group(7).strip() if match.group(7) else None
            declarations.append({
                "type": f"{const} {unsigned} {var_type} {pointer}".strip(),
                "name": var_name,
                "array": array,
                "value": var_value
            })
    return declarations

def extract_blocks(code):
    # Match block types and content
    block_pattern = r"(if|for|while|else)\s*\(.*?\)\s*{([\s\S]*?)}"
    blocks = []
    for block in re.finditer(block_pattern, code):
        block_type = block.group(1)
        block_body = block.group(2)
        block_declarations = extract_declarations(block_body)
        inner_blocks = extract_blocks(block_body)  # Recursive call for nested blocks
        blocks.append({
            "type": block_type,
            "declarations": block_declarations,
            "blocks": inner_blocks
        })
    return blocks

def build_hierarchy(code, global_vars, functions_metadata):
    hierarchy = {
        "global": global_vars,
        "functions": {}
    }

    for function_name, function_data in functions_metadata.items():
        function_hierarchy = {
            "arguments": function_data["arguments"],
            "declarations": [],
            "blocks": []
        }

        # Extract top-level declarations and nested blocks
        function_body = function_data["body"]
        function_hierarchy["declarations"] = extract_declarations(function_body)
        function_hierarchy["blocks"] = extract_blocks(function_body)

        hierarchy["functions"][function_name] = function_hierarchy

    return hierarchy

# Example Input Code
input_code = """
#include <stdio.h>

int globalVar = 42;
float globalFloat;
char *globalString = "Hello, World!";
const unsigned int globalArray[10] = {0};
double *globalPointer;

void myFunction() {
    int localVar = 10;
    if (localVar > 5) {
        int innerIfVar = 20;
    }
    for (int i = 0; i < 10; i++) {
        float loopVar = 3.14;
    }
}

int add(int a, int b) {
    int sum = a + b;
    return sum;
}
"""

# Extract Global Variables (Stage 3)
global_variables = stage3_extract_global_variables(input_code)

# Extract Functions Metadata (Stage 2)
functions_metadata = stage2_extract_functions(input_code)

# Build Hierarchy
hierarchy = build_hierarchy(input_code, global_variables, functions_metadata)

# Print Hierarchy
import pprint
pprint.pprint(hierarchy)
