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
    keywords: str = ""
    ptr_level: int = 0
    comments: Optional[str] = None
    rest: Optional[str] = None
    array: Optional[str] = None
    value: Optional[str] = None

@dataclass
class Method:
    """Represents a method within a struct."""
    comments: str
    return_type: str
    name: str
    arguments: List[Dict[str, Optional[str]]]
    body: str
    has_self: bool
    ptr_level: int = 0

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
    ptr_count = pointer.count("*")
    var_name = declaration.group(5).strip()
    array = declaration.group(6).strip() if declaration.group(6) else ""
    var_value = declaration.group(7).strip() if declaration.group(7) else None

    keywords = " ".join(filter(None, [const, unsigned]))
    if len(keywords) != 0:
        keywords = keywords + " "
    return Variable(type=var_type, keywords = keywords, name=var_name, array=array, value=var_value,ptr_level = ptr_count)

# Parser Class
class CodeParser:
    """
    Responsible for parsing the original code and extracting structured metadata.
    Parses structs, functions, global variables, and hierarchical blocks.
    """
    # Regex Patterns
    STRUCT_PATTERN = r"struct\s+(\w+)\s*\{((?:[^{}]*|\{[^{}]*\})*)\};"
    METHOD_PATTERN = r"((?:^[^\r\n]*\/\/.*\r?\n)*\s*)^\s*(\w+)\s+((?:\*\s*)*)?@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};"
    GLOBAL_PATTERN = r"((?:^[^\S\n]*\/\/.*$\r?\n)*)^[^\S\n\r]*\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+((?:\*\s*)*)?@(\w+)(.*)?\s*;"
    FUNCTION_PATTERN = r'\b([a-zA-Z_][a-zA-Z0-9_\s\*]*)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\{([\s\S]*?)\}'
    CONTROL_STRUCTURES = {
        "if", "for", "while", "switch", "else", "do", "case", "default", "goto", "return", "break", "continue"
    }
    GLOBAL_VAR_PATTERN = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)*([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    DECLARATION_PATTERN = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+((?:\*\s*)*)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[a-zA-Z0-9_]*\s*\])?\s*(=\s*[^;]+)?;"
    BLOCK_PATTERN = r"(if|for|while|else)\s*\(.*?\)\s*\{([\s\S]*?)\}"
    STRUCT_START = 'struct'
    STRUCT_END_CHAR = '}'

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
        def extract_structs(code: str) -> List[Tuple[str, str]]:
            structs = []
            struct_pattern = re.compile(r'struct\s+(\w+)\s*\{')

            lines = code.split('\n')
            i = 0
            while i < len(lines):
                match = struct_pattern.match(lines[i])
                if match:
                    struct_name = match.group(1)
                    struct_body = []
                    brace_count = 1
                    i += 1

                    while i < len(lines) and brace_count > 0:
                        line = lines[i].strip()
                        struct_body.append(line)
                        brace_count += line.count('{') - line.count('}')
                        i += 1

                    if brace_count == 0:
                        structs.append((struct_name, '\n'.join(struct_body[:-1])))  # Exclude the closing brace
                else:
                    i += 1

            return structs
        """Parses structs, extracting their variables, methods, and global variables."""
        logger.info("Starting Struct Parsing")
        for struct_name, struct_body in extract_structs(self.original_code):
            logger.debug(f"Processing struct: {struct_name}")

            metadata = StructMetadata()
            self.struct_metadata[struct_name] = metadata

            # Extract methods
            struct_body = re.sub(self.METHOD_PATTERN, lambda m: self.replace_method(m, struct_name, metadata), struct_body,flags=re.MULTILINE )
            # Extract globals
            print(f"struct body is {struct_body}")
            struct_body = re.sub(self.GLOBAL_PATTERN, lambda m: self.replace_global(m, struct_name, metadata), struct_body,flags=re.MULTILINE)
            print(f"globals struct body is {struct_body}")

            # Extract variables
            variable_matches = re.finditer(self.DECLARATION_PATTERN, struct_body)
            for var_match in variable_matches:
                variable = parse_variable_declaration(var_match)
                metadata.variables.append(variable)
                logger.debug(f"Extracted variable from struct '{struct_name}': {variable}")

            self.struct_metadata[struct_name] = metadata

            logger.info(f"\n\n{struct_name} metadata is {metadata}\n\n\n")
            logger.info(f"Completed parsing struct: {struct_name}")

    def replace_method(self, match: re.Match, struct_name: str, metadata: StructMetadata) -> str:
        """Extracts method details and updates struct metadata."""
        comments = match.group(1)
        return_type = match.group(2).strip()
        pointers_type = match.group(3).strip()
        ptr_count = pointers_type.count("*")
        method_name = match.group(4).strip()
        args = match.group(5).strip()
        body = match.group(6).strip()

        logger.debug(f"Extracting method: {method_name} from struct: {struct_name}")

        args_list = [arg.strip() for arg in args.split(',') if arg.strip()]
        has_self = False
        if args_list and re.match(rf"{struct_name}(?:_t)?\s+\*\s*self", args_list[0]):
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
            comments=comments,
            return_type=return_type,
            name=method_name,
            arguments=parsed_args,
            body=body,
            has_self=has_self,
            ptr_level=ptr_count
        )
        metadata.methods[method_name] = method

        logger.debug(f"Stored method metadata for '{method_name}': {method}")

        return ''  # Remove method from struct body

    def replace_global(self, match: re.Match, struct_name: str, metadata: StructMetadata) -> str:
        """Extracts global variable details and updates struct metadata."""
        comments = match.group(1).strip()
        const = match.group(2).strip() if match.group(2) else ""
        unsigned = match.group(3).strip() if match.group(3) else ""
        var_type = match.group(4).strip()
        pointer = match.group(5).strip() if match.group(5) else ""
        ptr_count = pointer.count("*")
        var_name = match.group(6).strip()
        rest = match.group(7).strip() if match.group(7) else ""

        keywords = " ".join(filter(None, [const, unsigned]))
        if len(keywords) != 0:
            keywords = keywords + ' '
        logger.debug(f"Extracting global variable: {var_name} from struct: {struct_name}")

        variable = Variable(type=var_type, name=var_name, keywords=keywords, comments=comments,ptr_level=ptr_count,rest=rest)
        metadata.globals[var_name] = variable

        logger.debug(f"Stored global variable metadata for '{var_name}': {variable}")
        print(f"found comment {comments}")

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
    METHOD_CALL_PATTERN = r"((?:\*)*)?(\b[a-zA-Z_][a-zA-Z0-9_]*@(?:\w+))\s*\(([^)]*)\)"

    def __init__(self, 
                 original_code: str, 
                 struct_metadata: Dict[str, StructMetadata], 
                 functions_metadata: Dict[str, FunctionMetadata], 
                 global_variables: List[Variable],
                 hierarchy: Hierarchy,
                 declare_in_place = False):
        self.original_code = original_code
        self.struct_metadata = struct_metadata
        self.functions_metadata = functions_metadata
        self.global_variables = global_variables
        self.hierarchy = hierarchy
        self.transformed_code = original_code  # Initialize with original code
        self.declare_in_place = declare_in_place
        self.pre_declarations = []

    def generate(self) -> str:
        """Generates the transformed code by applying all necessary replacements."""
        logger.info("Starting Code Generation")
        # Step 1: Replace all type usage with well defined _t precode
        logger.info("Fixing Types")
        self.fix_types();
        # Step 2: Replace Structs with transformed structs and methods
        logger.info("Replacing Structs")
        self.transformed_code = self.replace_structs()
        # Step 3: Refactor method calls with scope-aware replacements
        logger.info("Refactoring calls")
        self.transformed_code = self.refactor_method_calls_with_scope(self.transformed_code)
        # Step 4: Replace simple transforms
        logger.info("Simple replacements")
        self.transformed_code = self.replace_globals(self.transformed_code)
        self.transformed_code = self.replace_typecasts(self.transformed_code)
        self.transformed_code = self.replace_function_pointer(self.transformed_code)

        ## TODO @(dleiferives,7bbd9fd5-1b00-4f1c-bd20-48f312ec72ac): good place
        ## for header generation refactor ~#
        # Step 5: Generate declarations if need
        # typedefs
        # function pointers
        # normal structs
        # global structs
        # globals default assignment/ declaration
        #
        # member functions
        # everything else
        if not self.declare_in_place:
            logger.info("Inserting Declarations")
            self.transformed_code = "".join(self.pre_declarations) + self.transformed_code

        logger.info("Completed Code Generation")
        return self.transformed_code

    def fix_types(self):

        def fix_variable(var, name):
            print(f"checking var {var.type}")
            if var.type == name:
                var.type = struct_name + "_t"
            return var

        def fix_variables(vars: List, name):
            for iv, var in enumerate(vars):
                vars[iv] = fix_variable(var,name)
            return vars

        def fix_argument(arg,name):
            if 'type' in arg:
                print(f"checking arg {arg['type']}")
                if arg['type'] == name:
                    arg['type'] = name + "_t"
            return arg

        def fix_arguments(args,name):
            for ia, arg in enumerate(args):
                args[ia] = fix_argument(arg,name)
            return args



        def fix_method(method,name):
            print(f"checking method {method.return_type}")
            if method.return_type == name:
                method.return_type = name + "_t"

            method.arguments = fix_arguments(method.arguments,name)

            return method

        def fix_methods(methods,name):
            for method_name, value in methods.items():
                methods[method_name] = fix_method(value,name)
            return methods

        def fix_globals(gs,name):
            print("globals")
            for g_name, value in gs.items():
                print(f"global {g_name}")
                gs[g_name] = fix_variable(value,name)
            print("end globals")
            return gs

        def fix_struct(struct_name, new_name):
            fix_variables(self.struct_metadata[struct_name].variables, new_name)

            # fix methods
            fix_methods(self.struct_metadata[struct_name].methods,new_name)

            #fix globals
            fix_globals(self.struct_metadata[struct_name].globals,new_name)


        to_fix = []
        # read through all the structs
        for struct_name, body in self.struct_metadata.items():
            to_fix.append(struct_name)
            for name in to_fix:
                fix_struct(name, struct_name)
                fix_struct(struct_name, name)



        return None


    def replace_structs(self) -> str:
        """
        Reconstructs the structs with transformed methods and globals.
        Removes the original struct definitions from the code.
        """
        logger.info("Replacing structs with transformed structs and methods")
        transformed_structs = []
        code_lines = self.transformed_code.split('\n')
        new_code_lines = []
        i = 0
        n = len(code_lines)
        struct_pattern = re.compile(r'struct\s+(\w+)\s*\{')

        while i < n:
            line = code_lines[i]
            stripped_line = line.strip()

            match = struct_pattern.match(line)
            # Check if the line starts a struct definition
            if match:
                # Extract struct name

                struct_name = match.group(1)
                logger.debug(f"Found struct: {struct_name} at line {i+1}")

                # Initialize variables to capture the struct body
                struct_body_lines = []
                brace_count = 0

                # Check if '{' is on the same line
                if '{' in line:
                    brace_count += line.count('{')
                    brace_count -= line.count('}')
                    struct_body_lines.append(line[line.find('{') + 1:])
                else:
                    # Move to the next line to find '{'
                    i += 1
                    if i >= n:
                        logger.error(f"Struct {struct_name} not properly closed with '{{'")
                        break
                    line = code_lines[i]
                    brace_count += line.count('{')
                    brace_count -= line.count('}')
                    struct_body_lines.append(line[line.find('{') + 1:] if '{' in line else line)

                # Continue collecting struct body until all braces are closed
                while brace_count > 0 and i + 1 < n:
                    i += 1
                    line = code_lines[i]
                    brace_count += line.count('{')
                    brace_count -= line.count('}')
                    struct_body_lines.append(line)

                struct_body = '\n'.join(struct_body_lines).strip()
                logger.debug(f"Captured struct body for {struct_name}")

                # Process the struct if metadata is available
                if struct_name in self.struct_metadata:
                    metadata = self.struct_metadata[struct_name]
                    if metadata.done:
                        logger.debug(f"Struct {struct_name} already processed. Skipping.")
                        i += 1
                        continue

                    # Reconstruct the struct without methods and globals
                    struct_vars = [
                        f"{var.keywords} {var.type} {'*' * var.ptr_level}{var.name};"
                        for var in metadata.variables
                    ]
                    struct_body_reconstructed = '\n    '.join(struct_vars)

                    if struct_body_reconstructed.strip():
                        if not self.declare_in_place:
                            transpiled_struct = (
                                f"struct {struct_name}_s {{\n    {struct_body_reconstructed}\n}};\n"
                            )
                            transformed_structs.append(transpiled_struct)
                            transpiled_struct = (
                                f"typedef struct {struct_name}_s {struct_name}_t;\n"
                            )
                            self.pre_declarations.append(transpiled_struct)
                        else:
                            transpiled_struct = (
                                f"typedef struct {struct_name}_s {struct_name}_t;\n"
                                f"struct {struct_name}_s {{\n    {struct_body_reconstructed}\n}};\n"
                            )
                            transformed_structs.append(transpiled_struct)
                        logger.debug(f"Transpiled struct for {struct_name} added.")

                    # Handle globals if any
                    if metadata.globals:
                        globals_body = []
                        for var in metadata.globals.values():
                            var_declaration = f"    {var.keywords} {var.type} {'*' * var.ptr_level}{var.name};"
                            if var.comments:
                                globals_body.append(f"{var.comments}\n{var_declaration}")
                            else:
                                globals_body.append(var_declaration)
                        globals_body_reconstructed = '\n'.join(globals_body)
                        if not self.declare_in_place:
                            globals_struct = (
                                f"struct {struct_name}_globals_s {{\n{globals_body_reconstructed}\n}};\n"
                                f"{struct_name}_globals_t {struct_name}_globals;\n"
                            )
                            transformed_structs.append(globals_struct)
                            globals_struct = (
                                f"typedef struct {struct_name}_globals_s {struct_name}_globals_t;\n"
                            )
                            self.pre_declarations.append(globals_struct)
                        else:
                            globals_struct = (
                                f"typedef struct {struct_name}_globals_s {struct_name}_globals_t;\n"
                                f"struct {struct_name}_globals_s {{\n{globals_body_reconstructed}\n}};\n"
                                f"{struct_name}_globals_t {struct_name}_globals;\n"
                            )
                            transformed_structs.append(globals_struct)
                        logger.debug(f"Globals struct for {struct_name} added.")

                    # Generate transformed methods
                    for method in metadata.methods.values():
                        transformed_method = self.generate_transformed_method(struct_name, method)
                        transformed_structs.append(transformed_method)
                        logger.debug(f"Transformed method for {struct_name}: {method.name} added.")

                    # Mark the struct as processed
                    metadata.done = True
                    self.struct_metadata[struct_name] = metadata
                else:
                    logger.error(f"Could not find metadata for struct {struct_name}")

                # Append transformed structs instead of the original struct
                new_code_lines.extend(transformed_structs)
                transformed_structs = []
            else:
                # If not a struct definition, keep the line as is
                new_code_lines.append(line)

            i += 1

        # Join all lines to form the updated code
        code_with_updated_structs = '\n'.join(new_code_lines)
        logger.debug("Structs replaced successfully")
        return code_with_updated_structs

    def generate_transformed_method(self, struct_name: str, method: Method) -> str:
        """
        Generates the standalone function equivalent of a struct method.
        
        Args:
            struct_name (str): The name of the struct.
            method (Method): The method metadata.
        
        Returns:
            str: The transformed method as a standalone function.
        """
        arg_string = ', ' if len(method.arguments) >= 1 else ''
        transformed_args = ', '.join(
            f"{arg['type']} {arg['name']}" if arg['type'] else arg['name']
            for arg in method.arguments
        )
        if method.has_self:
            if not self.declare_in_place:
                transformed_function = (
                    f"{method.return_type} {'*' * method.ptr_level}{struct_name}_{method.name}({struct_name}_t *self{arg_string}{transformed_args});\n")
                self.pre_declarations.append(transformed_function)
            transformed_function = (
                f"{method.return_type} {'*' * method.ptr_level}{struct_name}_{method.name}({struct_name}_t *self{arg_string}{transformed_args}) {{\n"
                f"    {method.body}\n"
                f"}}\n"
            )
        else:
            if not self.declare_in_place:
                transformed_function = (
                    f"{method.return_type} {'*' * method.ptr_level}{struct_name}_{method.name}({transformed_args});\n")
                self.pre_declarations.append(transformed_function)
            transformed_function = (
                f"{method.return_type} {'*' * method.ptr_level}{struct_name}_{method.name}({transformed_args}) {{\n"
                f"    {method.body}\n"
                f"}}\n"
            )
        logger.debug(f"Generated transformed method:\n{transformed_function}")

        return "\n".join([line.strip() for line in method.comments.splitlines()]) + "\n" + transformed_function

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

            # Refactor method calls in the current line
            def replace_call(match: re.Match) -> str:
                full_call = match.group(0)
                ptr = match.group(1)
                ptr_count = ptr.count("*")
                method_call = match.group(2)
                args = match.group(3).strip()

                logger.debug(f"Refactoring method call: {full_call}")

                obj_or_type, method_name = method_call.split('@', 1)

                # Determine the type of obj_or_type by searching the symbol table stack
                obj_type, ptr_level, is_type= self.resolve_type(obj_or_type, symbol_table_stack)

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
                    ptr_level = ptr_count + ptr_level - 1
                    if(ptr_level < 0):
                        transformed_args = f"&{obj_or_type}"
                    else:
                        transformed_args = f"{'*' * ptr_level}{obj_or_type}"

                    if args:
                        transformed_args += f", {args}"
                else:
                    transformed_args = args

                transformed_args = transformed_args.strip().rstrip(',')

                transformed_call = f"{transformed_function_name}({transformed_args})"
                logger.debug(f"Transformed method call: {transformed_call}")
                return transformed_call


            # Handle variable declarations
            var_decl_match = re.match(CodeParser.DECLARATION_PATTERN, stripped_line)
            if var_decl_match:
                variable = parse_variable_declaration(var_decl_match)
                # Add to the current (top) symbol table
                symbol_table_stack[-1][variable.name] = variable
                new_line = []
                def update_declaration(match):
                    new_line.append(line[:match.end(3)] + "_t" + line[match.end(3):])

                if variable.type in self.struct_metadata:
                    re.sub(CodeParser.DECLARATION_PATTERN, update_declaration, line)
                    # Replace all method calls in the current line
                    try:
                        transformed_line = re.sub(self.METHOD_CALL_PATTERN, replace_call, new_line[0])
                        print(f"transformed line {transformed_line}")
                        transformed_lines.append(transformed_line)
                    except TransformationError as e:
                        logger.error(f"Error transforming line: {line}\n{e}")
                        transformed_lines.append(line)  # Optionally, you can choose to halt or handle differently
                    continue

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
            Tuple[Optional[str], bool, bool]: The type of the variable depth of its pointer, wether its a type
        """
        for symbol_table in reversed(symbol_table_stack):
            if var_name in symbol_table:
                var = symbol_table[var_name]
                var_type = var.type.replace('*', '').strip()
                logger.debug(f"Resolved type for variable '{var_name}': {var_type}, Pointer: {var.ptr_level}")
                return var_type, var.ptr_level, False
        # If not found in symbol tables, check if it's a type (static method)
        if var_name in self.struct_metadata:
            logger.debug(f"'{var_name}' identified as a type.")
            return var_name, 0, True
        return None, 0, False

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
            logger.info(f"checking {struct_name}");
            logger.debug(f"{struct_name} metadata is {metadata}");
            for global_member in metadata.globals.keys():
                logger.debug(f"member is {global_member}")
                pattern = rf'\b{struct_name}@{global_member}\b'
                replacement = f"({struct_name}_globals.{global_member})"
                updated_code = re.sub(pattern, replacement, updated_code)
                logger.debug(f"Replaced '{struct_name}@{global_member}' with '{replacement}'")
        logger.info("Global variable accesses replaced successfully")
        return updated_code

    def replace_typecasts(self, code: str) -> str:
        """
        Replaces occurrences of \(\s*StructType\s*((?:\*\s*)*)?\) with \(\s*StructType_t\s*((?:\*\s*)*)?\).

        Args:
            code (str): The code to process.

        Returns:
            str: The updated code with typecasts replaced.
        """
        logger.info("Replacing typecasts")
        updated_code = code
        for struct_name, metadata in self.struct_metadata.items():
            logger.info(f"checking {struct_name}");
            pattern = rf'\(\s*{struct_name}\s*((?:\*\s*)*)\)'
            replacement = rf'({struct_name}_t\1)'
            updated_code = re.sub(pattern, replacement, updated_code)
            logger.debug(f"Replaced typecasts for {struct_name}")
        logger.info("Typecasts replaced successfully")
        return updated_code

    def replace_function_pointer(self, code: str) -> str:
        """
        Replaces occurrences of StructType@method_name with  StructType_method_name

        Args:
            code (str): The code to process.

        Returns:
            str: The updated code with typecasts replaced.
        """
        logger.info("Replacing function pointers")
        updated_code = code
        for struct_name, metadata in self.struct_metadata.items():
            logger.info(f"checking {struct_name}");
            logger.debug(f"{struct_name} metadata is {metadata}");
            for method_name in metadata.methods.keys():
                logger.debug(f"found method {method_name}")
                pattern = rf'\b{struct_name}@{method_name}\b'
                replacement = f"({struct_name}_{method_name})"
                updated_code = re.sub(pattern, replacement, updated_code)
                logger.debug(f"Replaced '{struct_name}@{method_name}' with '{replacement}'")
        logger.info("Function pointer replacement completed")
        return updated_code

# Main Transformer Pipeline
class CodeTransformer:
    """
    Orchestrates the entire code transformation process by utilizing the CodeParser and CodeGenerator.
    """
    def __init__(self, code: str,declare_in_place=False):
        self.original_code = code
        self.transformed_code = code
        self.declare_in_place = declare_in_place
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
            hierarchy=self.hierarchy,
            declare_in_place=self.declare_in_place
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
    parser.add_argument("-dip", "--declare_in_place", help="Do declarations in place", default=False)
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

        transformer = CodeTransformer(input_code,declare_in_place=args.declare_in_place)
        transformer.run()

        with open(output_file, "w") as outfile:
            outfile.write(transformer.transformed_code)
            outfile.write(f"\n\n///////////////////////////////////////\n")
            outfile.write(f"// {output_file} autogenerated from {input_file}: \n")
            outfile.writelines(["// " + line for line in input_lines])

        logger.info(f"Transformation completed. Output written to {output_file}")
    except Exception as e:
        logger.error(f"Error during transformation: {e}")
        sys.exit(1)

# Example Usage
if __name__ == "__main__":
    main()
