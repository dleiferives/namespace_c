
import re

def extract_declarations(code):
    declaration_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
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
    # Regex to match blocks like if, for, while
    block_pattern = r"(if|for|while|else)\s*\(.*?\)\s*{([\s\S]*?)}"
    blocks = []
    for block in re.finditer(block_pattern, code):
        block_type = block.group(1)
        block_body = block.group(2).strip()
        block_declarations = extract_declarations(block_body)
        inner_blocks = extract_blocks(block_body)  # Recursive for nested blocks
        blocks.append({
            "type": block_type,
            "declarations": block_declarations,
            "blocks": inner_blocks
        })
    return blocks

def build_hierarchy(global_vars, functions_metadata):
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

        # Extract declarations and nested blocks from the function body
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

# Global Variables
def stage3_extract_global_variables(code):
    declaration_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    global_vars = []
    lines = code.splitlines()
    in_scope = True  # Assume global scope initially
    for line in lines:
        if "{" in line:
            in_scope = False
        if "}" in line:
            in_scope = True
            continue
        if in_scope:
            match = re.search(declaration_pattern, line.strip())
            if match:
                const = match.group(1).strip() if match.group(1) else ""
                unsigned = match.group(2).strip() if match.group(2) else ""
                var_type = match.group(3).strip()
                pointer = match.group(4).strip() if match.group(4) else ""
                var_name = match.group(5).strip()
                array = match.group(6).strip() if match.group(6) else ""
                var_value = match.group(7).strip() if match.group(7) else None
                global_vars.append({
                    "type": f"{const} {unsigned} {var_type} {pointer}".strip(),
                    "name": var_name,
                    "array": array,
                    "value": var_value
                })
    return global_vars

# Functions Metadata
def stage2_extract_functions(code):
    function_pattern = r"(\w+)\s*\(([\s\S]*?)\)\s*{([\s\S]*?)}"
    functions_metadata = {}
    functions = re.finditer(function_pattern, code)
    for function in functions:
        function_name = function.group(1)
        arguments = function.group(2).strip()
        body = function.group(3).strip()
        arguments_list = []
        for arg in arguments.split(','):
            arg = arg.strip()
            if arg:
                arg_parts = arg.split()
                if len(arg_parts) == 2:
                    arg_type, arg_name = arg_parts
                    arguments_list.append({"type": arg_type, "name": arg_name})
        functions_metadata[function_name] = {
            "arguments": arguments_list,
            "body": body
        }
    return functions_metadata

# Extract Global Variables
global_variables = stage3_extract_global_variables(input_code)

# Extract Functions Metadata
functions_metadata = stage2_extract_functions(input_code)

# Build Hierarchy
hierarchy = build_hierarchy(global_variables, functions_metadata)

# Print Hierarchy
import pprint
pprint.pprint(hierarchy)
