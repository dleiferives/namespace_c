import re
import pprint

# Stage 1: Transform Struct Methods into Standalone Functions
def stage1_transform_structs(code):
    """
    Transforms struct methods defined with @ syntax into standalone functions.
    Also extracts metadata about structs.
    """
    struct_pattern = r"struct\s+(\w+)\s*\{((?:[^{}]*|\{[^{}]*\})*)\};"
    method_pattern = r"(\w+)\s+@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};?"
    
    structs = re.finditer(struct_pattern, code)
    transpiled_code = []
    type_metadata = {}
    
    for struct in structs:
        struct_name = struct.group(1)
        struct_body = struct.group(2)
        
        # Initialize metadata for this struct
        type_metadata[struct_name] = {
            "variables": [],
            "methods": {}
        }
        
        # Extract methods and non-methods
        methods = re.finditer(method_pattern, struct_body)
        struct_body_without_methods = struct_body
        
        for method in methods:
            return_type = method.group(1).strip()
            method_name = method.group(2).strip()
            args = method.group(3).strip()
            body = method.group(4).strip()
            
            # Parse arguments
            args_list = [arg.strip() for arg in args.split(',') if arg.strip()]
            has_self = False
            if args_list and re.match(rf"{struct_name}\s*\*\s*\w+", args_list[0]):
                has_self = True
                args_list = args_list[1:]
            
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
            
            # Generate the transformed function
            transformed_args = ', '.join(
                f"{arg['type']} {arg['name']}" if arg['type'] else arg['name'] 
                for arg in parsed_args
            )
            if has_self:
                transformed_function = f"{return_type} {struct_name}_{method_name}({struct_name} *self, {transformed_args}) {{\n{body}\n}}\n"
            else:
                transformed_function = f"{return_type} {struct_name}_{method_name}({transformed_args}) {{\n{body}\n}}\n"
            transpiled_code.append(transformed_function)
            
            # Remove the method from struct body
            method_full = method.group(0)
            struct_body_without_methods = struct_body_without_methods.replace(method_full, '')
        
        # Extract variables (non-method contents)
        variable_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*;?"
        variables = re.finditer(variable_pattern, struct_body_without_methods)
        for var in variables:
            const = var.group(1).strip() if var.group(1) else ""
            unsigned = var.group(2).strip() if var.group(2) else ""
            var_type = var.group(3).strip()
            pointer = var.group(4).strip() if var.group(4) else ""
            var_name = var.group(5).strip()
            array = var.group(6).strip() if var.group(6) else ""
            type_metadata[struct_name]["variables"].append({
                "type": " ".join(filter(None, [const, unsigned, var_type, pointer])),
                "name": var_name,
                "array": array,
                "value": None
            })
        
        # Reconstruct the struct without methods
        struct_transformed_body = struct_body_without_methods.strip()
        transpiled_struct = f"struct {struct_name} {{\n{struct_transformed_body}\n}};\n"
        transpiled_code.insert(0, transpiled_struct)  # Insert struct first
    
    return "\n".join(transpiled_code), type_metadata

# Stage 2: Extract Function Definitions (excluding control structures)
def stage2_extract_functions(code):
    """
    Extracts function definitions from the code, excluding control structures.
    """
    control_structures = [
        "if", "for", "while", "switch", "else", "do", "case", "default", "goto", "return"
    ]
    control_structures_pattern = "|".join(control_structures)
    
    # Regex to match function definitions not preceded by control structures
    function_pattern = rf'\b(?!(?:{control_structures_pattern})\b)\b(\w+)\s*\(([^)]*)\)\s*\{{([\s\S]*?)\}}'
    
    functions_metadata = {}
    functions = re.finditer(function_pattern, code)
    for function in functions:
        function_name = function.group(1)
        arguments = function.group(2).strip()
        body = function.group(3).strip()
        
        # Skip if function_name is a control structure
        if function_name in control_structures:
            continue
        
        # Parse arguments
        arguments_list = []
        if arguments:
            for arg in arguments.split(','):
                arg = arg.strip()
                if arg:
                    # Handle pointers and multiple spaces
                    arg_parts = arg.rsplit(' ', 1)
                    if len(arg_parts) == 2:
                        arg_type, arg_name = arg_parts
                    else:
                        arg_type = None
                        arg_name = arg_parts[0]
                    arguments_list.append({"type": arg_type, "name": arg_name})
        
        functions_metadata[function_name] = {
            "arguments": arguments_list,
            "body": body
        }
    
    return functions_metadata

# Stage 3: Extract Global Variables
def stage3_extract_global_variables(code):
    """
    Extracts global variables from the code.
    """
    # Improved regex to capture global variables with better handling of complex types
    global_var_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    
    global_vars = []
    lines = code.splitlines()
    in_scope = False  # Start in global scope
    
    for line in lines:
        line = line.strip()
        
        # Update scope based on braces
        if '{' in line:
            in_scope = True
        if '}' in line:
            in_scope = False
            continue
        
        if not in_scope:
            match = re.match(global_var_pattern, line)
            if match:
                const = match.group(1).strip() if match.group(1) else ""
                unsigned = match.group(2).strip() if match.group(2) else ""
                var_type = match.group(3).strip()
                pointer = match.group(4).strip() if match.group(4) else ""
                var_name = match.group(5).strip()
                array = match.group(6).strip() if match.group(6) else ""
                var_value = match.group(7).strip() if match.group(7) else None
                
                full_type = " ".join(filter(None, [const, unsigned, var_type, pointer]))
                global_vars.append({
                    "type": full_type,
                    "name": var_name,
                    "array": array,
                    "value": var_value
                })
    
    return global_vars

# Stage 4: Build Hierarchical Dictionary
def build_hierarchy(global_vars, functions_metadata):
    """
    Builds a hierarchical dictionary capturing global variables, functions, and nested blocks within functions.
    """
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
        
        function_body = function_data["body"]
        
        # Extract top-level declarations
        function_hierarchy["declarations"] = extract_declarations(function_body)
        
        # Extract nested blocks
        function_hierarchy["blocks"] = extract_blocks(function_body)
        
        hierarchy["functions"][function_name] = function_hierarchy
    
    return hierarchy

def extract_declarations(code):
    """
    Extracts variable declarations from a code block.
    """
    # Regex to match variable declarations
    declaration_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    skip_keywords = ["return", "break", "continue", "goto", "switch", "case", "default", "do"]
    
    declarations = []
    lines = code.splitlines()
    
    for line in lines:
        line = line.strip()
        
        # Skip lines that start with control flow keywords
        if any(line.startswith(kw + ' ') or line == kw for kw in skip_keywords):
            continue
        
        match = re.match(declaration_pattern, line)
        if match:
            const = match.group(1).strip() if match.group(1) else ""
            unsigned = match.group(2).strip() if match.group(2) else ""
            var_type = match.group(3).strip()
            pointer = match.group(4).strip() if match.group(4) else ""
            var_name = match.group(5).strip()
            array = match.group(6).strip() if match.group(6) else ""
            var_value = match.group(7).strip() if match.group(7) else None
            
            full_type = " ".join(filter(None, [const, unsigned, var_type, pointer]))
            declarations.append({
                "type": full_type,
                "name": var_name,
                "array": array,
                "value": var_value
            })
    
    return declarations

def extract_blocks(code):
    """
    Recursively extracts nested blocks like if, for, while, else from a code block.
    """
    # Regex to match blocks like if, for, while, else
    block_pattern = r"(if|for|while|else)\s*\(.*?\)\s*\{([\s\S]*?)\}"
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
    
    # Stage 2: Extract Function Definitions
    functions_metadata = stage2_extract_functions(input_code)
    print("\n=== Functions Metadata (Stage 2) ===\n")
    pprint.pprint(functions_metadata)
    
    # Stage 3: Extract Global Variables
    global_variables = stage3_extract_global_variables(input_code)
    print("\n=== Global Variables (Stage 3) ===\n")
    pprint.pprint(global_variables)
    
    # Stage 4: Build Hierarchy
    hierarchy = build_hierarchy(global_variables, functions_metadata)
    print("\n=== Hierarchical Declarations (Stage 4) ===\n")
    pprint.pprint(hierarchy)
