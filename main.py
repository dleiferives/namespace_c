import re
import pprint
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import logging
import argparse

logger = logging.getLogger(__name__)
# Configure logging
def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.ERROR
    logging.basicConfig(level=level, format="%(message)s")

# Custom Exceptions
class TransformationError(Exception):
    """Custom exception for transformation errors."""
    pass

# Data Classes for Structured Metadata
@dataclass
class Variable:
    """Represents a variable with its type, name, optional array dimensions, and initial value."""
    type: str
    name: str
    array: Optional[str] = None
    value: Optional[str] = None

@dataclass
class Method:
    """Represents a method within a struct."""
    return_type: str
    name: str
    arguments: List[Dict[str, Optional[str]]]
    body: str
    has_self: bool

@dataclass
class StructMetadata:
    """Holds variables, methods, and global variables associated with a struct."""
    variables: List[Variable] = field(default_factory=list)
    methods: Dict[str, Method] = field(default_factory=dict)
    globals: Dict[str, Variable] = field(default_factory=dict)
    done = False

@dataclass
class FunctionMetadata:
    """Contains details about a function."""
    return_type: str
    name: str
    arguments: List[Dict[str, Optional[str]]]
    body: str

@dataclass
class HierarchicalBlock:
    """Represents a nested block within a function (e.g., within an if or for statement)."""
    type: str
    declarations: List[Variable]
    blocks: List['HierarchicalBlock']

@dataclass
class FunctionHierarchy:
    """Organizes the hierarchical structure of a function."""
    arguments: List[Dict[str, Optional[str]]]
    declarations: List[Variable]
    blocks: List[HierarchicalBlock]

@dataclass
class Hierarchy:
    """Aggregates global variables and functions with their hierarchical structures."""
    global_vars: List[Variable]
    functions: Dict[str, FunctionHierarchy] = field(default_factory=dict)

# Utility Functions
def parse_variable_declaration(declaration: re.Match) -> Variable:
    """
    Parses a variable declaration from a regex match and returns a Variable instance.
    
    Args:
        declaration (re.Match): The regex match containing variable details.
    
    Returns:
        Variable: The parsed variable.
    """
    const = declaration.group(1).strip() if declaration.group(1) else ""
    unsigned = declaration.group(2).strip() if declaration.group(2) else ""
    var_type = declaration.group(3).strip()
    pointer = declaration.group(4).strip() if declaration.group(4) else ""
    var_name = declaration.group(5).strip()
    array = declaration.group(6).strip() if declaration.group(6) else ""
    var_value = declaration.group(7).strip() if declaration.group(7) else None

    full_type = " ".join(filter(None, [const, unsigned, var_type, pointer]))
    return Variable(type=full_type, name=var_name, array=array, value=var_value)

# Parser Class
class CodeParser:
    """
    Responsible for parsing the original code and extracting structured metadata.
    Parses structs, functions, global variables, and hierarchical blocks.
    """
    # Regex Patterns
    STRUCT_PATTERN = r"struct\s+(\w+)\s*\{((?:[^{}]*|\{[^{}]*\})*)\};"
    METHOD_PATTERN = r"(\w+)\s+@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};?"
    GLOBAL_PATTERN = r"(\w+)\s+@(\w+)\s*;"
    FUNCTION_PATTERN = r'\b([a-zA-Z_][a-zA-Z0-9_\s\*]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\{([\s\S]*?)\}'
    CONTROL_STRUCTURES = {
        "if", "for", "while", "switch", "else", "do", "case", "default", "goto", "return", "break", "continue"
    }
    GLOBAL_VAR_PATTERN = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    DECLARATION_PATTERN = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    BLOCK_PATTERN = r"(if|for|while|else)\s*\(.*?\)\s*\{([\s\S]*?)\}"

    def __init__(self, code: str):
        self.original_code = code
        self.struct_metadata: Dict[str, StructMetadata] = {}
        self.functions_metadata: Dict[str, FunctionMetadata] = {}
        self.global_variables: List[Variable] = []

    def parse(self):
        """Parses the entire code, extracting structs, functions, globals, and hierarchy."""
        self.parse_structs()
        self.parse_functions()
        self.parse_globals()

    def parse_structs(self):
        """Parses structs, extracting their variables, methods, and global variables."""
        logger.info("Starting Struct Parsing")
        struct_matches = re.finditer(self.STRUCT_PATTERN, self.original_code)
        for match in struct_matches:
            struct_name = match.group(1)
            struct_body = match.group(2)
            logger.debug(f"Processing struct: {struct_name}")

            metadata = StructMetadata()
            self.struct_metadata[struct_name] = metadata

            # Extract methods
            struct_body = re.sub(self.METHOD_PATTERN, lambda m: self.replace_method(m, struct_name, metadata), struct_body)
            # Extract globals
            struct_body = re.sub(self.GLOBAL_PATTERN, lambda m: self.replace_global(m, struct_name, metadata), struct_body)

            # Extract variables
            variable_matches = re.finditer(self.DECLARATION_PATTERN, struct_body)
            for var_match in variable_matches:
                variable = parse_variable_declaration(var_match)
                metadata.variables.append(variable)
                logger.debug(f"Extracted variable from struct '{struct_name}': {variable}")

            logger.info(f"Completed parsing struct: {struct_name}")

    def replace_method(self, match: re.Match, struct_name: str, metadata: StructMetadata) -> str:
        """Extracts method details and updates struct metadata."""
        return_type = match.group(1).strip()
        method_name = match.group(2).strip()
        args = match.group(3).strip()
        body = match.group(4).strip()

        logger.debug(f"Extracting method: {method_name} from struct: {struct_name}")

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

        method = Method(
            return_type=return_type,
            name=method_name,
            arguments=parsed_args,
            body=body,
            has_self=has_self
        )
        metadata.methods[method_name] = method

        logger.debug(f"Stored method metadata for '{method_name}': {method}")

        return ''  # Remove method from struct body

    def replace_global(self, match: re.Match, struct_name: str, metadata: StructMetadata) -> str:
        """Extracts global variable details and updates struct metadata."""
        var_type = match.group(1).strip()
        var_name = match.group(2).strip()

        logger.debug(f"Extracting global variable: {var_name} from struct: {struct_name}")

        variable = Variable(type=var_type, name=var_name)
        metadata.globals[var_name] = variable

        logger.debug(f"Stored global variable metadata for '{var_name}': {variable}")

        return ''  # Remove global from struct body

    def parse_functions(self):
        """Parses function definitions, excluding control structures."""
        logger.info("Starting Function Parsing")
        function_matches = re.finditer(self.FUNCTION_PATTERN, self.original_code)
        for match in function_matches:
            return_type = match.group(1).strip()
            function_name = match.group(2).strip()
            arguments = match.group(3).strip()
            body = match.group(4).strip()

            if function_name in self.CONTROL_STRUCTURES:
                logger.debug(f"Skipping control structure function: {function_name}")
                continue

            arguments_list = self.parse_arguments(arguments)
            function_metadata = FunctionMetadata(
                return_type=return_type,
                name=function_name,
                arguments=arguments_list,
                body=body
            )
            self.functions_metadata[function_name] = function_metadata

            logger.debug(f"Extracted function metadata: {function_name}")
        logger.info("Completed Function Parsing")

    def parse_arguments(self, arguments: str) -> List[Dict[str, Optional[str]]]:
        """Parses function arguments into a structured format."""
        args_list = []
        if arguments:
            for arg in arguments.split(','):
                arg = arg.strip()
                if arg:
                    parts = arg.rsplit(' ', 1)
                    if len(parts) == 2:
                        arg_type, arg_name = parts
                    else:
                        arg_type = None
                        arg_name = parts[0]
                    args_list.append({"type": arg_type, "name": arg_name})
        return args_list

    def parse_globals(self):
        """Parses global variable declarations outside of any struct or function."""
        logger.info("Starting Global Variable Parsing")
        lines = self.original_code.splitlines()
        in_scope = False  # Tracks if currently within a scope (e.g., inside a function or struct)

        for line in lines:
            stripped_line = line.strip()

            # Update scope based on braces
            if '{' in stripped_line:
                in_scope = True
            if '}' in stripped_line:
                in_scope = False
                continue

            if not in_scope:
                match = re.match(self.GLOBAL_VAR_PATTERN, stripped_line)
                if match:
                    variable = parse_variable_declaration(match)
                    self.global_variables.append(variable)
                    logger.debug(f"Extracted global variable: {variable}")

        logger.info("Completed Global Variable Parsing")

# Generator Class
class CodeGenerator:
    """
    Utilizes the extracted metadata to generate the transformed code.
    Handles method call refactoring and global variable replacement.
    """
    METHOD_CALL_PATTERN = r"(\b[a-zA-Z_][a-zA-Z0-9_]*@(?:\w+))\s*\(([^)]*)\)"

    def __init__(self, 
                 original_code: str, 
                 struct_metadata: Dict[str, StructMetadata], 
                 functions_metadata: Dict[str, FunctionMetadata], 
                 global_variables: List[Variable],
                 hierarchy: Hierarchy):
        self.original_code = original_code
        self.struct_metadata = struct_metadata
        self.functions_metadata = functions_metadata
        self.global_variables = global_variables
        self.hierarchy = hierarchy
        self.transformed_code = original_code  # Initialize with original code

    def generate(self) -> str:
        """Generates the transformed code by applying all necessary replacements."""
        logger.info("Starting Code Generation")
        # Step 1: Replace Structs with transformed structs and methods
        self.transformed_code = self.replace_structs()
        # Step 2: Refactor method calls with scope-aware replacements
        self.transformed_code = self.refactor_method_calls_with_scope(self.transformed_code)
        # Step 3: Replace global variable accesses
        self.transformed_code = self.replace_globals(self.transformed_code)
        logger.info("Completed Code Generation")
        return self.transformed_code

    def replace_structs(self) -> str:
        """
        Reconstructs the structs with transformed methods and globals.
        Removes the original struct definitions from the code.
        """
        logger.info("Replacing structs with transformed structs and methods")
        def replace_struct(match: re.Match) -> str:
            transformed_structs = []
            full_def = match.group(0)
            name = match.group(1)
            body = match.group(2).strip()
            if name in self.struct_metadata:
                struct_name = name;
                metadata = self.struct_metadata[name]
                if metadata.done == True:
                    return ''
                # Reconstruct the struct without methods and globals
                struct_body = '\n    '.join([f"{var.type} {var.name};" for var in metadata.variables])
                transpiled_struct = (
                    f"typedef struct {struct_name}_s {struct_name};\n"
                    f"struct {struct_name}_s {{\n    {struct_body}\n}};\n"
                )
                transformed_structs.append(transpiled_struct)

                # Handle globals
                if metadata.globals:
                    globals_body = '\n    '.join([f"{var.type} {var.name};" for var in metadata.globals.values()])
                    globals_struct = (
                        f"typedef struct {struct_name}_globals_s {struct_name}_globals_t;\n"
                        f"struct {struct_name}_globals_s {{\n    {globals_body}\n}};\n"
                        f"{struct_name}_globals_t {struct_name}_globals;\n"
                    )
                    transformed_structs.append(globals_struct)

                # Generate transformed methods
                for method in metadata.methods.values():
                    transformed_method = self.generate_transformed_method(struct_name, method)
                    transformed_structs.append(transformed_method)
                metadata.done = True
                self.struct_metadata[name] = metadata
            else:
                logger.error(f"could not find struct {name}")

            # Remove original struct definitions
            # Here, we assume that the transformed structs should replace the original ones.
            # For simplicity, we'll prepend the transformed structs to the code.
            final_code = '\n'.join(transformed_structs) + '\n' 
            return final_code
        code_without_structs = re.sub(CodeParser.STRUCT_PATTERN, replace_struct, self.transformed_code)
        # Insert transformed structs at the beginning
        logger.debug("Structs replaced successfully")
        return code_without_structs

    def generate_transformed_method(self, struct_name: str, method: Method) -> str:
        """
        Generates the standalone function equivalent of a struct method.
        
        Args:
            struct_name (str): The name of the struct.
            method (Method): The method metadata.
        
        Returns:
            str: The transformed method as a standalone function.
        """
        transformed_args = ', '.join(
            f"{arg['type']} {arg['name']}" if arg['type'] else arg['name']
            for arg in method.arguments
        )
        if method.has_self:
            transformed_function = (
                f"{method.return_type} {struct_name}_{method.name}({struct_name} *self, {transformed_args}) {{\n"
                f"    {method.body}\n"
                f"}}\n"
            )
        else:
            transformed_function = (
                f"{method.return_type} {struct_name}_{method.name}({transformed_args}) {{\n"
                f"    {method.body}\n"
                f"}}\n"
            )
        logger.debug(f"Generated transformed method:\n{transformed_function}")
        return transformed_function

    def refactor_method_calls_with_scope(self, code: str) -> str:
        """
        Refactors method calls using the @ syntax to standard C function calls with scope-aware replacements.
        
        Args:
            code (str): The code to refactor.
        
        Returns:
            str: The refactored code.
        """
        logger.info("Refactoring method calls with scope-aware replacements")
        
        # We'll process the code block by block, replacing method calls with scope-aware type resolution
        # This requires parsing the code to identify scopes and track variable types

        # Initialize symbol table stack with global scope
        symbol_table_stack = [self.build_global_symbol_table()]
        
        # Split code into lines for processing
        lines = code.splitlines()
        transformed_lines = []
        brace_stack = []  # To track the current scope based on braces

        for line in lines:
            stripped_line = line.strip()
            
            # Entering a new block
            if re.search(r'\{', stripped_line):
                # Push a new symbol table for the new scope
                symbol_table_stack.append({})
                brace_stack.append('{')
            # Exiting a block
            if re.search(r'\}', stripped_line):
                if brace_stack:
                    brace_stack.pop()
                if symbol_table_stack:
                    symbol_table_stack.pop()
                transformed_lines.append(line)
                continue

            # Handle variable declarations
            var_decl_match = re.match(CodeParser.DECLARATION_PATTERN, stripped_line)
            if var_decl_match:
                variable = parse_variable_declaration(var_decl_match)
                # Add to the current (top) symbol table
                symbol_table_stack[-1][variable.name] = variable
                transformed_lines.append(line)
                continue

            # Refactor method calls in the current line
            def replace_call(match: re.Match) -> str:
                full_call = match.group(0)
                method_call = match.group(1)
                args = match.group(2).strip()

                logger.debug(f"Refactoring method call: {full_call}")

                obj_or_type, method_name = method_call.split('@', 1)

                # Determine the type of obj_or_type by searching the symbol table stack
                obj_type, obj_pointer, is_type= self.resolve_type(obj_or_type, symbol_table_stack)

                if not obj_type:
                    error_msg = f"Unable to determine type for '{obj_or_type}' in method call '{full_call}'."
                    logger.error(error_msg)
                    raise TransformationError(error_msg)

                # Retrieve method metadata
                if obj_type not in self.struct_metadata:
                    error_msg = f"Type '{obj_type}' not found for method '{method_name}' in call '{full_call}'."
                    logger.error(error_msg)
                    raise TransformationError(error_msg)

                if method_name not in self.struct_metadata[obj_type].methods:
                    error_msg = f"Method '{method_name}' not found in type '{obj_type}' for call '{full_call}'."
                    logger.error(error_msg)
                    raise TransformationError(error_msg)

                method_meta = self.struct_metadata[obj_type].methods[method_name]

                # Determine transformed function name
                transformed_function_name = f"{obj_type}_{method_name}"

                # Build transformed arguments
                if method_meta.has_self and not is_type:
                    if obj_pointer:
                        transformed_args = obj_or_type
                    else:
                        transformed_args = f"&{obj_or_type}"
                    if args:
                        transformed_args += f", {args}"
                else:
                    transformed_args = args

                transformed_args = transformed_args.strip().rstrip(',')

                transformed_call = f"{transformed_function_name}({transformed_args})"
                logger.debug(f"Transformed method call: {transformed_call}")
                return transformed_call

            # Replace all method calls in the current line
            try:
                transformed_line = re.sub(self.METHOD_CALL_PATTERN, replace_call, line)
                transformed_lines.append(transformed_line)
            except TransformationError as e:
                logger.error(f"Error transforming line: {line}\n{e}")
                transformed_lines.append(line)  # Optionally, you can choose to halt or handle differently

        transformed_code = '\n'.join(transformed_lines)
        logger.info("Method calls refactored successfully with scope awareness")
        return transformed_code

    def resolve_type(self, var_name: str, symbol_table_stack: List[Dict[str, Variable]]) -> Tuple[Optional[str], bool, bool]:
        """
        Resolves the type of a variable by searching through the symbol table stack.

        Args:
            var_name (str): The name of the variable.
            symbol_table_stack (List[Dict[str, Variable]]): The stack of symbol tables representing scopes.

        Returns:
            Tuple[Optional[str], bool, bool]: The type of the variable and whether it's a pointer, wether its a type
        """
        for symbol_table in reversed(symbol_table_stack):
            if var_name in symbol_table:
                var = symbol_table[var_name]
                is_pointer = '*' in var.type
                var_type = var.type.replace('*', '').strip()
                logger.debug(f"Resolved type for variable '{var_name}': {var_type}, Pointer: {is_pointer}")
                return var_type, is_pointer, False
        # If not found in symbol tables, check if it's a type (static method)
        if var_name in self.struct_metadata:
            logger.debug(f"'{var_name}' identified as a type.")
            return var_name, False, True
        return None, False, False

    def build_global_symbol_table(self) -> Dict[str, Variable]:
        """
        Builds the global symbol table from the global variables.

        Returns:
            Dict[str, Variable]: The global symbol table.
        """
        global_symbol_table = {var.name: var for var in self.global_variables}
        logger.debug(f"Global symbol table: {global_symbol_table}")
        return global_symbol_table

    def replace_globals(self, code: str) -> str:
        """
        Replaces occurrences of StructType@member with StructType_globals.member.
        
        Args:
            code (str): The code to process.
        
        Returns:
            str: The updated code with globals replaced.
        """
        logger.info("Replacing global variable accesses")
        updated_code = code
        for struct_name, metadata in self.struct_metadata.items():
            for global_member in metadata.globals.keys():
                pattern = rf'\b{struct_name}@{global_member}\b'
                replacement = f"({struct_name}_globals.{global_member})"
                updated_code = re.sub(pattern, replacement, updated_code)
                logger.debug(f"Replaced '{struct_name}@{global_member}' with '{replacement}'")
        logger.info("Global variable accesses replaced successfully")
        return updated_code

# Main Transformer Pipeline
class CodeTransformer:
    """
    Orchestrates the entire code transformation process by utilizing the CodeParser and CodeGenerator.
    """
    def __init__(self, code: str):
        self.original_code = code
        self.transformed_code = code
        self.struct_metadata: Dict[str, StructMetadata] = {}
        self.functions_metadata: Dict[str, FunctionMetadata] = {}
        self.global_variables: List[Variable] = []
        self.hierarchy: Hierarchy = Hierarchy(global_vars=[])

    def run(self):
        """Executes the parsing and generation stages to transform the code."""
        logger.info("Starting Code Transformation Pipeline")

        # Stage 1: Parse the code
        parser = CodeParser(self.original_code)
        parser.parse()
        self.struct_metadata = parser.struct_metadata
        self.functions_metadata = parser.functions_metadata
        self.global_variables = parser.global_variables

        # Stage 2: Build hierarchy
        self.hierarchy = Hierarchy(
            global_vars=self.global_variables,
            functions=self.build_function_hierarchy()
        )

        # Stage 3: Generate transformed code
        generator = CodeGenerator(
            original_code=self.original_code,
            struct_metadata=self.struct_metadata,
            functions_metadata=self.functions_metadata,
            global_variables=self.global_variables,
            hierarchy=self.hierarchy
        )
        self.transformed_code = generator.generate()

        logger.info("Code Transformation Pipeline completed successfully")

    def build_function_hierarchy(self) -> Dict[str, FunctionHierarchy]:
        """
        Builds a hierarchical structure for each function, including declarations and nested blocks.
        
        Returns:
            Dict[str, FunctionHierarchy]: The hierarchical structure of functions.
        """
        logger.info("Building hierarchical declarations for functions")
        hierarchy_parser = HierarchyParser(self.global_variables, self.functions_metadata)
        hierarchy_parser.parse_hierarchy()
        return hierarchy_parser.hierarchy.functions

    def display_results(self):
        """Prints out the transformed code and associated metadata."""
        print("=== Final Refactored Code ===\n")
        print(self.transformed_code)
        
        print("\n=== Struct Metadata ===\n")
        pprint.pprint(self.struct_metadata)
        
        print("\n=== Functions Metadata ===\n")
        pprint.pprint(self.functions_metadata)
        
        print("\n=== Global Variables ===\n")
        pprint.pprint(self.global_variables)
        
        print("\n=== Hierarchical Declarations ===\n")
        pprint.pprint(self.hierarchy)

# Hierarchy Parser Class (Helper for CodeTransformer)
class HierarchyParser:
    """
    Builds a hierarchical representation of global variables and functions, including nested blocks within functions.
    """
    def __init__(self, global_vars: List[Variable], functions_metadata: Dict[str, FunctionMetadata]):
        self.global_vars = global_vars
        self.functions_metadata = functions_metadata
        self.hierarchy = Hierarchy(global_vars=self.global_vars)

    def parse_hierarchy(self):
        """Constructs the hierarchy by processing function metadata."""
        logger.info("Starting Hierarchical Declarations Parsing")
        for func_name, func_meta in self.functions_metadata.items():
            declarations = self.extract_declarations(func_meta.body)
            blocks = self.extract_blocks(func_meta.body)
            self.hierarchy.functions[func_name] = FunctionHierarchy(
                arguments=func_meta.arguments,
                declarations=declarations,
                blocks=blocks
            )
            logger.debug(f"Built hierarchy for function: {func_name}")
        logger.info("Completed Hierarchical Declarations Parsing")

    def extract_declarations(self, code: str) -> List[Variable]:
        """
        Extracts variable declarations from a code block.
        
        Args:
            code (str): The code block to parse.
        
        Returns:
            List[Variable]: The list of extracted declarations.
        """
        declaration_pattern = CodeParser.DECLARATION_PATTERN
        skip_keywords = {"return", "break", "continue", "goto", "switch", "case", "default", "do"}

        declarations = []
        lines = code.splitlines()

        for line in lines:
            stripped_line = line.strip()
            if any(stripped_line.startswith(kw + ' ') or stripped_line == kw for kw in skip_keywords):
                continue

            match = re.match(declaration_pattern, stripped_line)
            if match:
                variable = parse_variable_declaration(match)
                declarations.append(variable)
                logger.debug(f"Extracted declaration: {variable}")

        return declarations

    def extract_blocks(self, code: str) -> List[HierarchicalBlock]:
        """
        Recursively extracts nested blocks like if, for, while, else from a code block.
        
        Args:
            code (str): The code block to parse.
        
        Returns:
            List[HierarchicalBlock]: The list of extracted blocks.
        """
        block_pattern = CodeParser.BLOCK_PATTERN
        blocks = []

        for block in re.finditer(block_pattern, code):
            block_type = block.group(1)
            block_body = block.group(2).strip()
            block_declarations = self.extract_declarations(block_body)
            inner_blocks = self.extract_blocks(block_body)  # Recursive for nested blocks
            hierarchical_block = HierarchicalBlock(
                type=block_type,
                declarations=block_declarations,
                blocks=inner_blocks
            )
            blocks.append(hierarchical_block)
            logger.debug(f"Extracted block: {block_type}")

        return blocks

# Entry point for file-based processing
def main():
    parser = argparse.ArgumentParser(description="Transform C-like code.")
    parser.add_argument("input_file", help="Path to the input file")
    parser.add_argument("-o", "--output_file", help="Path to the output file (optional)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    setup_logging(args.verbose)

    input_file = args.input_file
    output_file = args.output_file

    # Default output file logic
    if not output_file:
        if input_file.endswith(".d"):
            output_file = input_file.rsplit(".", 1)[0] + ".c"
        else:
            logger.error("Output file must be specified for non-.d input files.")
            sys.exit(1)

    try:
        with open(input_file, "r") as infile:
            input_code = infile.read()
        with open(input_file, "r") as infile:
            input_lines = infile.readlines()

        transformer = CodeTransformer(input_code)
        transformer.run()

        with open(output_file, "w") as outfile:
            outfile.write(transformer.transformed_code)
            outfile.write(f"\n\n///////////////////////////////////////\n")
            outfile.write(f"// {input_file} source pre transform\n")
            outfile.writelines(["// " + line for line in input_lines])

        logger.info(f"Transformation completed. Output written to {output_file}")
    except Exception as e:
        logger.error(f"Error during transformation: {e}")
        sys.exit(1)

# Example Usage
if __name__ == "__main__":
    main()
