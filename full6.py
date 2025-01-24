
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Data Classes for Structured Metadata
@dataclass
class Variable:
    type: str
    name: str
    array: Optional[str] = None
    value: Optional[str] = None

@dataclass
class Method:
    return_type: str
    name: str
    arguments: List[Dict[str, Optional[str]]]
    body: str
    has_self: bool = False

@dataclass
class StructMetadata:
    variables: List[Variable] = field(default_factory=list)
    methods: Dict[str, Method] = field(default_factory=dict)
    globals: Dict[str, Variable] = field(default_factory=dict)

@dataclass
class FunctionMetadata:
    return_type: str
    name: str
    arguments: List[Dict[str, Optional[str]]]
    body: str

@dataclass
class Hierarchy:
    global_vars: List[Variable]
    functions: Dict[str, FunctionMetadata] = field(default_factory=dict)

# Utility Functions
def parse_arguments(arg_string: str) -> List[Dict[str, Optional[str]]]:
    """Parses function or method arguments into structured format."""
    args = [arg.strip() for arg in arg_string.split(',') if arg.strip()]
    return [{"type": arg.rsplit(' ', 1)[0], "name": arg.rsplit(' ', 1)[1]} if ' ' in arg else {"type": None, "name": arg} for arg in args]

def parse_variable_declaration(match: re.Match) -> Variable:
    """Parses a variable declaration into a structured Variable instance."""
    full_type = " ".join(filter(None, [match.group(1), match.group(2), match.group(3), match.group(4)]))
    return Variable(type=full_type.strip(), name=match.group(5).strip(), array=match.group(6), value=match.group(7))

# Parser Class
class CodeParser:
    STRUCT_PATTERN = r"struct\s+(\w+)\s*\{((?:[^{}]*|\{[^{}]*\})*)\};"
    METHOD_PATTERN = r"(\w+)\s+@(\w+)\s*\(([^)]*)\)\s*\{([\s\S]*?)\};?"
    DECLARATION_PATTERN = r"\b(const\s+)?(unsigned\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(\*\s*)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(\[\s*[^\]]*\])?\s*(=\s*[^;]+)?;"

    def __init__(self, code: str):
        self.original_code = code
        self.struct_metadata: Dict[str, StructMetadata] = {}

    def parse(self):
        """Parses structs and methods."""
        struct_matches = re.finditer(self.STRUCT_PATTERN, self.original_code)
        for match in struct_matches:
            struct_name, body = match.group(1), match.group(2)
            metadata = StructMetadata()
            self.struct_metadata[struct_name] = metadata

            # Extract and replace methods
            body = re.sub(self.METHOD_PATTERN, lambda m: self._parse_method(m, struct_name, metadata), body)

            # Parse variables
            for var_match in re.finditer(self.DECLARATION_PATTERN, body):
                metadata.variables.append(parse_variable_declaration(var_match))

    def _parse_method(self, match: re.Match, struct_name: str, metadata: StructMetadata) -> str:
        """Parses methods into structured metadata."""
        method = Method(
            return_type=match.group(1),
            name=match.group(2),
            arguments=parse_arguments(match.group(3)),
            body=match.group(4),
            has_self=struct_name in match.group(3)
        )
        metadata.methods[method.name] = method
        return ''  # Remove method from struct body

# Example Usage
if __name__ == "__main__":
    code = """
    struct MyType {
        int x;
        int @add(MyType *self, int a) { return self->x + a; };
    };
    """
    parser = CodeParser(code)
    parser.parse()
    print(parser.struct_metadata)
