import re

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

# Example Input
input_code = """
int add(int a, int b) {
    return a + b;
}

void printMessage(char *message) {
    printf("%s", message);
}

float multiply(float x, float y) {
    return x * y;
}
"""

# Extract Function Metadata
functions_metadata = stage2_extract_functions(input_code)

# Print Metadata
import pprint
pprint.pprint(functions_metadata)
