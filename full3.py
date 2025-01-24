
import re
import pprint
import sys

def stage1_transform_structs(code):
    """
    Transforms struct methods defined with @ syntax into standalone functions.
    Also extracts metadata about structs.
    """
    struct_pattern = r"struct\s+(\w+)\s*\{((?:[^{}]*|\{[^{}]*\})*)\};"
    method_pattern = r"(\w+)\s+@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};?"
    global_pattern = r"(\w+)\s+@(\w+)\s*;" 

    type_metadata = {}
    
    def replace_struct(struct_match):
        struct_name = struct_match.group(1)
        struct_body = struct_match.group(2)
        
        # Initialize metadata for this struct
        type_metadata[struct_name] = {
            "variables": [],
            "methods": {},
            "globals": {}
        }
        
        transformed_methods = []
        transformed_globals = []
        
        def replace_method(method_match):
            return_type = method_match.group(1).strip()
            method_name = method_match.group(2).strip()
            args = method_match.group(3).strip()
            body = method_match.group(4).strip()
            
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
            transformed_methods.append(transformed_function)
            
            return ''  # Remove the method from struct body

        def replace_global(global_match):
            var_type = global_match.group(1).strip()
            var_name = global_match.group(2).strip()
            
            # Store global metadata
            type_metadata[struct_name]["globals"][var_name] = {
                "type": var_type
            }
            
            # Generate the transformed global declaration
            transformed_global = f"{var_type} {var_name};\n"
            transformed_globals.append(transformed_global)
            
            return ''  # Remove the global from struct body
        
        struct_body_without_methods = re.sub(method_pattern, replace_method, struct_body)
        struct_body_without_globals = re.sub(global_pattern, replace_global, struct_body_without_methods)
        
        # Extract variables (non-method contents)
        variable_pattern = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*;?"
        variables = re.finditer(variable_pattern, struct_body_without_globals)
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
        struct_transformed_body = struct_body_without_globals.strip()
        transpiled_struct = f"typedef struct {struct_name}_s {struct_name};\nstruct {struct_name}_s {{\n{struct_transformed_body}\n}};\n"
        globals_list = '\n'.join(transformed_globals)
        gloabals_struct = f"typedef struct {struct_name}_globals_s {struct_name}_globals_t;\nstruct {struct_name}_globals_s{{\n{globals_list}}};\n{struct_name}_globals_t {struct_name}_globals;"
        
        return transpiled_struct + '\n\n' + gloabals_struct + '\n' + '\n'.join(transformed_methods)
    
    transpiled_code = re.sub(struct_pattern, replace_struct, code)
    
    return transpiled_code, type_metadata

# Stage 2: Extract Function Definitions (excluding control structures)
def stage2_extract_functions(code):
    """
    Extracts function definitions from the code, excluding control structures.
    """
    control_structures = [
        "if", "for", "while", "switch", "else", "do", "case", "default", "goto", "return", "break", "continue"
    ]
    control_structures_pattern = "|".join(control_structures)
    
    # Regex to match function definitions not starting with control structures
    # This regex ensures that the function has a return type and a valid name
    # It avoids matching control structures by ensuring the name is not a keyword
    function_pattern = rf'\b([a-zA-Z_][a-zA-Z0-9_\s\*]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\{{([\s\S]*?)\}}'
    
    functions_metadata = {}
    functions = re.finditer(function_pattern, code)
    for function in functions:
        return_type = function.group(1).strip()
        function_name = function.group(2).strip()
        arguments = function.group(3).strip()
        body = function.group(4).strip()
        
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
            "return_type": return_type,
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

# Stage 5: Refactor Method Calls with Parameter Validation
def stage5_refactor_method_calls(code, hierarchy, type_metadata):
    """
    Refactors method calls in the code:
    - Transforms 'a@add(20)' to 'MyType_add(&a, 20)'
    - Transforms 'b@add(20)' to 'MyType_add(b, 20)'
    - Transforms 'MyType@add(&a, 20)' to 'MyType_add(&a, 20)'
    
    Additionally, checks parameters and raises errors if inconsistencies are found.
    
    Args:
        code (str): The original C code as a string.
        hierarchy (dict): The hierarchical dictionary from Stage 4.
        type_metadata (dict): The type metadata from Stage 1.
    
    Returns:
        str: The refactored C code with method calls transformed.
    """
    
    # Regex pattern to identify method calls using '@'
    method_call_pattern = r"(\b[a-zA-Z_][a-zA-Z0-9_]*@(?:\w+))\s*\(([^)]*)\)"
    
    def replace_method_call(match):
        full_call = match.group(0)        # Entire matched method call, e.g., 'a@add(20)'
        method_call = match.group(1)      # e.g., 'a@add'
        args = match.group(2).strip()     # e.g., '20'
        
        # Split method_call into object/type and method name
        if '@' in method_call:
            obj_or_type, method_name = method_call.split('@', 1)
        else:
            # This should not happen as per the regex, but handle gracefully
            return full_call
        
        # Determine if obj_or_type is a variable (instance method) or a type (static method)
        is_type = False
        obj_type = None
        obj_pointer = False
        
        # Check if obj_or_type is a global variable
        for var in hierarchy.get("global", []):
            if var["name"] == obj_or_type:
                obj_type = var["type"].replace('*', '').strip()
                obj_pointer = '*' in var["type"]
                break
        else:
            # Check within function declarations
            for func in hierarchy.get("functions", {}).values():
                for var in func.get("declarations", []):
                    if var["name"] == obj_or_type:
                        obj_type = var["type"].replace('*', '').strip()
                        obj_pointer = '*' in var["type"]
                        break
                if obj_type:
                    break
        
            if not obj_type:
                # Assume obj_or_type is a type if it exists in type_metadata or follows naming conventions
                if obj_or_type in type_metadata or re.match(r'^[A-Z][a-zA-Z0-9_]*$', obj_or_type):
                    is_type = True
                    obj_type = obj_or_type
                else:
                    print(f"Error: Undefined type or variable '{obj_or_type}' used in method call '{full_call}'.", file=sys.stderr)
                    sys.exit(1)
        
        if not obj_type:
            print(f"Error: Unable to determine type for '{obj_or_type}' in method call '{full_call}'.", file=sys.stderr)
            sys.exit(1)
        
        # Retrieve method metadata
        if is_type:
            # Static method: check in type_metadata
            if obj_type not in type_metadata:
                print(f"Error: Type '{obj_type}' not found for static method '{method_name}'.", file=sys.stderr)
                sys.exit(1)
            if method_name not in type_metadata[obj_type]["methods"]:
                print(f"Error: Method '{method_name}' not found in type '{obj_type}'.", file=sys.stderr)
                sys.exit(1)
            method_meta = type_metadata[obj_type]["methods"][method_name]
            has_self = False
        else:
            # Instance method: check in type_metadata
            if obj_type not in type_metadata:
                print(f"Error: Type '{obj_type}' not found for instance method '{method_name}'.", file=sys.stderr)
                sys.exit(1)
            if method_name not in type_metadata[obj_type]["methods"]:
                print(f"Error: Method '{method_name}' not found in type '{obj_type}'.", file=sys.stderr)
                sys.exit(1)
            method_meta = type_metadata[obj_type]["methods"][method_name]
            has_self = method_meta.get("has_self", False)
        
        # Expected arguments
        expected_args = method_meta.get("arguments", [])
        num_expected_args = len(expected_args)
        
        # Parse provided arguments
        provided_args = [arg.strip() for arg in args.split(',')] if args else []
        num_provided_args = len(provided_args)
        
        # Validate argument count
        if is_type:
            # Static method: all arguments are provided explicitly
            if num_provided_args != num_expected_args + 1:
                print(f"Error: Method '{method_name}' of type '{obj_type}' expects {num_expected_args} arguments, but {num_provided_args} were provided in '{full_call}'.", file=sys.stderr)
                sys.exit(1)
        else:
            # Instance method: arguments are provided explicitly; 'self' is handled automatically
            if num_provided_args != num_expected_args:
                print(f"Error: Method '{method_name}' of type '{obj_type}' expects {num_expected_args} arguments, but {num_provided_args} were provided in '{full_call}'.", file=sys.stderr)
                sys.exit(1)
        
        # Determine transformed function name
        transformed_function_name = f"{obj_type}_{method_name}"
        
        # Build transformed arguments
        if is_type or not has_self:
            # Static method: pass arguments as provided
            transformed_args = args
        else:
            # Instance method: pass 'self' automatically
            if obj_pointer:
                # 'obj_or_type' is a pointer; pass as-is
                transformed_args = obj_or_type
            else:
                # 'obj_or_type' is not a pointer; pass reference
                transformed_args = f"&{obj_or_type}"
            
            if args:
                transformed_args += f", {args}"
        
        # Clean up transformed_args
        transformed_args = transformed_args.strip().rstrip(',')
        
        return f"{transformed_function_name}({transformed_args})"
    
    # Replace all method calls in the code
    refactored_code = re.sub(method_call_pattern, replace_method_call, code)
    
    return refactored_code

def stage6_replace_globals(code, type_metadata):
    """
    Replaces occurrences of StructType@member with StructType_globals.member in the code.

    Args:
        code (str): The C code to process.
        type_metadata (dict): Metadata about structs, including globals.

    Returns:
        str: The updated C code with globals replaced.
    """
    updated_code = code

    # Iterate over each struct in the metadata
    for struct_name, struct_info in type_metadata.items():
        globals_info = struct_info.get("globals", {})
        if not globals_info:
            continue  # Skip structs without globals

        # Iterate over each global member in the struct
        for global_member in globals_info.keys():
            # Create a regex pattern to match StructType@member with word boundaries
            pattern = rf'\b{struct_name}@{global_member}\b'

            # Replacement string
            replacement = f"({struct_name}_globals.{global_member})"

            # Perform the replacement
            updated_code = re.sub(pattern, replacement, updated_code)

    return updated_code



# struct MyType {
#     int x;
#     int @y;
#     int @add(MyType *self, int a) {
#         self->x += a;
#         return self->x;
#     };
#
#     int @increment(int value) {
#         return value + 1;
#     };
# }
#
# - >
#
# typedef struct MyType_s MyType;
# struct MyType_s {
#     int x;
# };
#
# typedef struct MyType_globals_s MyType_globals_t;
# struct MyType_globals_s{
#     int y;
# }
#
# MyType_globals_t MyType_globals;
#
# int MyType_add(MyType *self, int a) {
# self->x += a;
#             return self->x;
# }
#
# int MyType_increment(int value) {
# return value + 1;
# }



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
        int @y;
        int @add(MyType *self, int a) {
            self->x += a;
            return self->x;
        };
    
        int @increment(int value) {
            return value + 1;
        };
        int @global_increment(int value) {
            return value + MyType@y;
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
        b@add(MyType@y->a.b);
        MyType@add(b,20);
    }
    
    int add(int a, int b) {
        int sum = a + b;
        return sum;
    }
    """
    
    # Stage 1: Transform Structs & create globals
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
    
    # Stage 5: Refactor Method Calls
    refactored_code = stage5_refactor_method_calls(transformed_code, hierarchy, type_metadata)
    print("\n=== Refactored Code (Stage 5) ===\n")
    print(refactored_code)


    # Stage 6: Refactor Method Calls
    refactored_code = stage6_replace_globals(refactored_code, type_metadata)
    print("\n=== Refactored Code (Stage 6) ===\n")
    print(refactored_code)

