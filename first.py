import re
import pprint

# Stage 1: Transform Struct Methods into Standalone Functions and Replace Structs In-Place
def stage1_transform_structs(code):
    """
    Transforms struct methods defined with @ syntax into standalone functions.
    Modifies the original code by removing methods from structs and adding standalone functions.
    Replaces the original struct definitions in the code with the transformed ones.
    Also extracts metadata about structs.
    
    Args:
        code (str): The original C code as a string.
    
    Returns:
        tuple:
            - str: The transformed C code with structs modified and standalone functions inserted.
            - dict: The type metadata containing information about structs, their variables, and methods.
    """
    # Regex patterns
    struct_pattern = r"struct\s+(\w+)\s*\{([\s\S]*?)\};"
    method_pattern = r"(\w+)\s+@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};?"
    
    # Initialize metadata and a list to hold standalone functions
    type_metadata = {}
    standalone_functions = []
    
    # Function to process each struct and perform transformations
    def process_struct(match):
        struct_name = match.group(1)      # e.g., 'MyType'
        struct_body = match.group(2)      # Content inside the struct
        
        # Initialize metadata for this struct
        type_metadata[struct_name] = {
            "variables": [],
            "methods": {}
        }
        
        # Find all methods within the struct
        methods = list(re.finditer(method_pattern, struct_body))
        struct_body_without_methods = struct_body  # To store struct content without methods
        
        for method in methods:
            return_type = method.group(1).strip()   # e.g., 'int'
            method_name = method.group(2).strip()   # e.g., 'add'
            args = method.group(3).strip()          # e.g., 'MyType *self, int a'
            body = method.group(4).strip()          # Method body
            
            # Parse arguments
            args_list = [arg.strip() for arg in args.split(',') if arg.strip()]
            has_self = False
            if args_list and re.match(rf"{struct_name}\s*\*\s*\w+", args_list[0]):
                has_self = True
                args_list = args_list[1:]  # Remove 'self' from arguments
            
            parsed_args = []
            for arg in args_list:
                parts = arg.rsplit(' ', 1)
                if len(parts) == 2:
                    arg_type, arg_name = parts
                else:
                    arg_type = None
                    arg_name = parts[0]
                parsed_args.append({"type": arg_type, "name": arg_name})
            
            # Store method metadata
            type_metadata[struct_name]["methods"][method_name] = {
                "return_type": return_type,
                "arguments": parsed_args,
                "has_self": has_self
            }
            
            # Generate the transformed standalone function
            transformed_args = ', '.join(
                f"{arg['type']} {arg['name']}" if arg['type'] else arg['name'] 
                for arg in parsed_args
            )
            if has_self:
                transformed_function = f"{return_type} {struct_name}_{method_name}({struct_name} *self, {transformed_args}) {{\n{body}\n}}\n"
            else:
                transformed_function = f"{return_type} {struct_name}_{method_name}({transformed_args}) {{\n{body}\n}}\n"
            standalone_functions.append(transformed_function)
            
            # Remove the method from struct body
            method_full = method.group(0)
            struct_body_without_methods = struct_body_without_methods.replace(method_full, '')
        
        # Extract variables (non-method contents)
        # Improved variable pattern to handle multiple declarations and pointers
        variable_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*\w*\s*\])?\s*;?"
        variables = re.finditer(variable_pattern, struct_body_without_methods)
        for var in variables:
            const = var.group(1).strip() if var.group(1) else ""
            unsigned = var.group(2).strip() if var.group(2) else ""
            var_type = var.group(3).strip()
            pointer = var.group(4).strip() if var.group(4) else ""
            var_name = var.group(5).strip()
            array = var.group(6).strip() if var.group(6) else ""
            full_type = " ".join(filter(None, [const, unsigned, var_type, pointer]))
            type_metadata[struct_name]["variables"].append({
                "type": full_type,
                "name": var_name,
                "array": array,
                "value": None
            })
        
        # Reconstruct the struct without methods
        struct_transformed_body = struct_body_without_methods.strip()
        # Handle empty structs gracefully
        if struct_transformed_body.endswith(';'):
            struct_transformed_body = struct_transformed_body[:-1].strip()
        transpiled_struct = f"struct {struct_name} {{\n    {struct_transformed_body}\n}};\n"
        
        return transpiled_struct
    
    # Replace all structs in the code with their transformed versions
    transformed_code = re.sub(struct_pattern, process_struct, code)
    
    # Insert the standalone functions immediately after their corresponding struct definitions
    # We'll iterate through the transformed_code and for each struct, append its functions right after
    # To achieve this, we need to process the code line by line
    lines = transformed_code.splitlines()
    final_code_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        final_code_lines.append(line)
        
        # Check if this line is the end of a struct definition
        struct_end_pattern = r"};"
        if re.match(struct_end_pattern, line.strip()):
            # Find the struct name from the previous lines
            j = i - 1
            struct_name = None
            while j >= 0:
                struct_decl_pattern = r"struct\s+(\w+)\s*\{"
                struct_decl_match = re.match(struct_decl_pattern, lines[j].strip())
                if struct_decl_match:
                    struct_name = struct_decl_match.group(1)
                    break
                j -= 1
            if struct_name:
                # Append all standalone functions for this struct
                for func in standalone_functions.copy():
                    func_struct_pattern = rf"{struct_name}_\w+"
                    func_name = func.split()[1].split('(')[0]  # Extract function name
                    if re.match(func_struct_pattern, func_name):
                        final_code_lines.append(func)
                        standalone_functions.remove(func)
        
        i += 1
    
    # Append any remaining standalone functions at the end of the code
    if standalone_functions:
        final_code_lines.append("\n")
        final_code_lines.extend(standalone_functions)
    
    # Join all lines back into a single string
    final_code = "\n".join(final_code_lines)
    
    return final_code, type_metadata



# Example Usage
if __name__ == "__main__":
    # Example Input Code
    input_code = """
    #include <stdio.h>
    
    int globalVar = 42;
    float globalFloat;
    char *globalString = "Hello, World!";
    const unsigned int globalArray[10] = {0};
    double *globalPointer;
    
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
    
    void myFunction() {
        int localVar = 10;
        if (localVar > 5) {
            int innerIfVar = 20;
            if (innerIfVar > 15) {
                int nestedIfVar = 30;
            }
        }
        for (int i = 0; i < 10; i++) {
            float loopVar = 3.14;
            for (int j = 0; j < 5; j++) {
                int nestedForVar = 50;
            }
        }
        MyType a;
        a@increment(10);
        a@add(5);
        MyType *b;
        b@add(10);
        MyType@add(&a, 20);
    }
    
    int add(int a, int b) {
        int sum = a + b;
        return sum;
    }
    """
    
    # Stage 1: Transform Structs
    transformed_code, type_metadata = stage1_transform_structs(input_code)
    
    print("=== Transformed Code (Stage 1) ===\n")
    print(transformed_code)
    
    print("\n=== Type Metadata ===\n")
    pprint.pprint(type_metadata)
