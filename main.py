import re

def stage1_transform_with_metadata(code):
    # Regex to match structs and methods with improved method pattern
    struct_pattern = r"struct\s+(\w+)\s*\{((?:[^{}]*|\{[^{}]*\})*)\};"
    method_pattern = r"(\w+)\s+@(\w+)\(([\s\S]*?)\)\s*{([\s\S]*?)};"

    # Dictionary to store metadata about types
    type_metadata = {}

    # Match structs
    structs = re.finditer(struct_pattern, code)
    transpiled_code = []

    for struct in structs:
        struct_name = struct.group(1)
        struct_body = struct.group(2)
        struct_transformed_body = re.sub(method_pattern, '', struct_body).strip()

        # Initialize metadata for this struct
        type_metadata[struct_name] = {
            "variables": [],
            "methods": {}
        }

        # Extract variables (non-method contents)
        variable_pattern = r"(\w+)\s+(\w+);"
        variables = re.finditer(variable_pattern, struct_transformed_body)
        for var in variables:
            var_type = var.group(1)
            var_name = var.group(2)
            type_metadata[struct_name]["variables"].append({"type": var_type, "name": var_name})

        # Transform struct definition (without methods)
        transpiled_code.append(f"struct {struct_name} {{\n{struct_transformed_body}\n}};\n")

        # Match methods within the struct
        methods = re.finditer(method_pattern, struct_body)
        for method in methods:
            return_type = method.group(1)
            method_name = method.group(2)
            args = method.group(3)
            body = method.group(4)

            # Check if the first argument is self (struct pointer)
            args_list = [arg.strip() for arg in args.split(',') if arg.strip()]
            has_self = len(args_list) > 0 and struct_name + " *self" in args_list[0]
            
            # Remove self argument if present
            if has_self:
                args_list = args_list[1:]

            # Store method metadata
            type_metadata[struct_name]["methods"][method_name] = {
                "return_type": return_type,
                "arguments": [{"type": arg.split()[0], "name": arg.split()[1]} for arg in args_list if " " in arg],
                "has_self": has_self
            }

            # Generate the transformed function
            transformed_args = ', '.join(arg.strip() for arg in args_list)
            if has_self:
                transformed_function = f"{return_type} {struct_name}_{method_name}({struct_name} *self, {transformed_args}) {{\n{body}\n}}\n"
            else:
                transformed_function = f"{return_type} {struct_name}_{method_name}({transformed_args}) {{\n{body}\n}}\n"
            transpiled_code.append(transformed_function)

    return "\n".join(transpiled_code), type_metadata


def stage2_extract_code_blocks_and_variables(code):
    # Match all blocks enclosed in `{ ... }` and find variables defined inside
    block_pattern = r"{([\s\S]*?)}"
    variable_pattern = r"(\w+)\s+(\w+);"

    # Store block information
    blocks_metadata = []
    blocks = re.finditer(block_pattern, code)

    for block in blocks:
        block_content = block.group(1)
        variables = []

        # Match variables within the block
        for var in re.finditer(variable_pattern, block_content):
            var_type = var.group(1)
            var_name = var.group(2)
            variables.append({"type": var_type, "name": var_name})

        blocks_metadata.append({
            "block_content": block_content.strip(),
            "variables": variables
        })

    return blocks_metadata


# Example Input
input_code = """
struct MyType {
    int x;
    int @add(MyType *self, int a) {
        self->x += a;
        return self->x;
    };

    int @increment(int value) {
        return value + 1;
    };
};

int main() {
    int a = 10;
    {
        int b = 20;
        {
            int c = 30;
        }
    }
    return 0;
}
"""

# Stage 1: Transpile Code and Extract Metadata
output_code, metadata = stage1_transform_with_metadata(input_code)

# Stage 2: Extract Code Blocks and Variables
blocks_metadata = stage2_extract_code_blocks_and_variables(input_code)

# Print Transformed Code (Stage 1)
print("Transformed Code:")
print(output_code)

# Print Metadata (Stage 1)
print("\nMetadata:")
import pprint
pprint.pprint(metadata)

# Print Block Metadata (Stage 2)
print("\nBlock Metadata:")
pprint.pprint(blocks_metadata)
