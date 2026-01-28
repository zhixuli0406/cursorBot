"""
Auto-Documentation Generator for CursorBot

Automatically generate documentation from code.

Features:
- Docstring extraction and formatting
- API documentation generation
- README generation
- Changelog generation
- Code structure visualization
- Multiple output formats (Markdown, HTML, RST)

Usage:
    from src.core.auto_docs import get_doc_generator, DocConfig
    
    generator = get_doc_generator()
    
    # Generate docs for a module
    docs = await generator.generate_module_docs("src/core/rag.py")
    
    # Generate project README
    readme = await generator.generate_readme(".")
    
    # Generate API reference
    api_docs = await generator.generate_api_docs("src/")
"""

import ast
import asyncio
import inspect
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union

from ..utils.logger import logger


# ============================================
# Documentation Types
# ============================================

class DocFormat(Enum):
    """Output documentation formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    RST = "rst"
    JSON = "json"


class DocType(Enum):
    """Types of documentation elements."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    VARIABLE = "variable"
    CONSTANT = "constant"


@dataclass
class DocParameter:
    """Documentation for a function parameter."""
    name: str
    type_hint: str = ""
    description: str = ""
    default: str = ""
    required: bool = True


@dataclass
class DocReturn:
    """Documentation for a return value."""
    type_hint: str = ""
    description: str = ""


@dataclass
class DocElement:
    """A documentation element (function, class, etc.)."""
    name: str
    doc_type: DocType
    docstring: str = ""
    signature: str = ""
    
    # For functions/methods
    parameters: list[DocParameter] = field(default_factory=list)
    returns: Optional[DocReturn] = None
    raises: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    
    # For classes
    bases: list[str] = field(default_factory=list)
    methods: list["DocElement"] = field(default_factory=list)
    attributes: list["DocElement"] = field(default_factory=list)
    
    # Metadata
    file_path: str = ""
    line_number: int = 0
    is_async: bool = False
    is_static: bool = False
    is_classmethod: bool = False
    is_property: bool = False
    decorators: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.doc_type.value,
            "docstring": self.docstring,
            "signature": self.signature,
            "parameters": [
                {"name": p.name, "type": p.type_hint, "description": p.description, "default": p.default}
                for p in self.parameters
            ],
            "returns": {"type": self.returns.type_hint, "description": self.returns.description} if self.returns else None,
            "raises": self.raises,
            "examples": self.examples,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


@dataclass
class ModuleDoc:
    """Documentation for a module."""
    name: str
    path: str
    docstring: str = ""
    elements: list[DocElement] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "docstring": self.docstring,
            "elements": [e.to_dict() for e in self.elements],
            "imports": self.imports,
        }


@dataclass
class DocConfig:
    """Configuration for documentation generation."""
    # Output options
    format: DocFormat = DocFormat.MARKDOWN
    include_private: bool = False
    include_dunder: bool = False
    include_source: bool = False
    
    # Content options
    include_examples: bool = True
    include_type_hints: bool = True
    include_inheritance: bool = True
    
    # README options
    readme_sections: list[str] = field(default_factory=lambda: [
        "overview", "installation", "usage", "api", "examples", "contributing", "license"
    ])
    
    # AI enhancement
    use_ai_enhancement: bool = False
    ai_model: str = ""


# ============================================
# Code Parser
# ============================================

class CodeParser:
    """Parse Python code to extract documentation elements."""
    
    def __init__(self, config: DocConfig = None):
        self.config = config or DocConfig()
    
    def parse_file(self, file_path: str) -> ModuleDoc:
        """Parse a Python file and extract documentation."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = path.read_text(encoding="utf-8")
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return ModuleDoc(name=path.stem, path=str(path))
        
        module_doc = ModuleDoc(
            name=path.stem,
            path=str(path),
            docstring=ast.get_docstring(tree) or "",
        )
        
        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_doc.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                for alias in node.names:
                    module_doc.imports.append(f"{module_name}.{alias.name}")
        
        # Extract elements
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                if self._should_include(node.name):
                    class_doc = self._parse_class(node, file_path)
                    module_doc.elements.append(class_doc)
            
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if self._should_include(node.name):
                    func_doc = self._parse_function(node, file_path)
                    module_doc.elements.append(func_doc)
            
            elif isinstance(node, ast.Assign):
                # Module-level constants
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if target.id.isupper() and self._should_include(target.id):
                            const_doc = DocElement(
                                name=target.id,
                                doc_type=DocType.CONSTANT,
                                file_path=file_path,
                                line_number=node.lineno,
                            )
                            module_doc.elements.append(const_doc)
        
        return module_doc
    
    def _should_include(self, name: str) -> bool:
        """Check if an element should be included based on config."""
        if name.startswith("__") and name.endswith("__"):
            return self.config.include_dunder
        if name.startswith("_"):
            return self.config.include_private
        return True
    
    def _parse_class(self, node: ast.ClassDef, file_path: str) -> DocElement:
        """Parse a class definition."""
        class_doc = DocElement(
            name=node.name,
            doc_type=DocType.CLASS,
            docstring=ast.get_docstring(node) or "",
            file_path=file_path,
            line_number=node.lineno,
            bases=[self._get_name(base) for base in node.bases],
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
        )
        
        # Parse methods and attributes
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self._should_include(item.name):
                    method_doc = self._parse_function(item, file_path)
                    method_doc.doc_type = DocType.METHOD
                    
                    # Check for property decorator
                    for dec in item.decorator_list:
                        dec_name = self._get_decorator_name(dec)
                        if dec_name == "property":
                            method_doc.is_property = True
                            method_doc.doc_type = DocType.PROPERTY
                        elif dec_name == "staticmethod":
                            method_doc.is_static = True
                        elif dec_name == "classmethod":
                            method_doc.is_classmethod = True
                    
                    class_doc.methods.append(method_doc)
            
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                # Class attribute with type annotation
                attr_doc = DocElement(
                    name=item.target.id,
                    doc_type=DocType.VARIABLE,
                    signature=self._get_annotation(item.annotation) if item.annotation else "",
                    file_path=file_path,
                    line_number=item.lineno,
                )
                class_doc.attributes.append(attr_doc)
        
        return class_doc
    
    def _parse_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], file_path: str) -> DocElement:
        """Parse a function definition."""
        is_async = isinstance(node, ast.AsyncFunctionDef)
        
        func_doc = DocElement(
            name=node.name,
            doc_type=DocType.FUNCTION,
            docstring=ast.get_docstring(node) or "",
            file_path=file_path,
            line_number=node.lineno,
            is_async=is_async,
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
        )
        
        # Parse parameters
        args = node.args
        defaults = args.defaults
        num_defaults = len(defaults)
        num_args = len(args.args)
        
        for i, arg in enumerate(args.args):
            if arg.arg == "self" or arg.arg == "cls":
                continue
            
            param = DocParameter(name=arg.arg)
            
            if arg.annotation:
                param.type_hint = self._get_annotation(arg.annotation)
            
            # Check for default value
            default_index = i - (num_args - num_defaults)
            if default_index >= 0:
                param.default = self._get_default_value(defaults[default_index])
                param.required = False
            
            func_doc.parameters.append(param)
        
        # Handle *args and **kwargs
        if args.vararg:
            func_doc.parameters.append(DocParameter(
                name=f"*{args.vararg.arg}",
                type_hint=self._get_annotation(args.vararg.annotation) if args.vararg.annotation else "",
                required=False,
            ))
        
        if args.kwarg:
            func_doc.parameters.append(DocParameter(
                name=f"**{args.kwarg.arg}",
                type_hint=self._get_annotation(args.kwarg.annotation) if args.kwarg.annotation else "",
                required=False,
            ))
        
        # Parse return type
        if node.returns:
            func_doc.returns = DocReturn(type_hint=self._get_annotation(node.returns))
        
        # Parse docstring for more details
        if func_doc.docstring:
            self._parse_docstring(func_doc)
        
        # Build signature
        func_doc.signature = self._build_signature(func_doc)
        
        return func_doc
    
    def _get_name(self, node: ast.AST) -> str:
        """Get the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        return ""
    
    def _get_decorator_name(self, node: ast.AST) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""
    
    def _get_annotation(self, node: ast.AST) -> str:
        """Get type annotation as string."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_annotation(node.value)}[{self._get_annotation(node.slice)}]"
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._get_annotation(e) for e in node.elts)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return f"{self._get_annotation(node.left)} | {self._get_annotation(node.right)}"
        return ""
    
    def _get_default_value(self, node: ast.AST) -> str:
        """Get default value as string."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return "[]"
        elif isinstance(node, ast.Dict):
            return "{}"
        elif isinstance(node, ast.Call):
            return f"{self._get_name(node.func)}()"
        return "..."
    
    def _parse_docstring(self, doc: DocElement) -> None:
        """Parse docstring to extract parameters, returns, raises, examples."""
        docstring = doc.docstring
        
        # Parse Google-style or NumPy-style docstrings
        sections = re.split(r'\n\s*(Args|Parameters|Returns|Raises|Examples|Example):\s*\n', docstring)
        
        current_section = None
        for i, section in enumerate(sections):
            section_lower = section.lower().strip()
            
            if section_lower in ("args", "parameters"):
                current_section = "params"
            elif section_lower == "returns":
                current_section = "returns"
            elif section_lower == "raises":
                current_section = "raises"
            elif section_lower in ("examples", "example"):
                current_section = "examples"
            elif current_section == "params":
                # Parse parameter descriptions
                for line in section.split("\n"):
                    match = re.match(r'\s*(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.*)', line)
                    if match:
                        param_name = match.group(1)
                        param_type = match.group(2) or ""
                        param_desc = match.group(3)
                        
                        # Update existing parameter
                        for param in doc.parameters:
                            if param.name == param_name:
                                if not param.type_hint and param_type:
                                    param.type_hint = param_type
                                param.description = param_desc
                                break
            
            elif current_section == "returns":
                if doc.returns:
                    doc.returns.description = section.strip()
                else:
                    doc.returns = DocReturn(description=section.strip())
            
            elif current_section == "raises":
                for line in section.split("\n"):
                    line = line.strip()
                    if line:
                        doc.raises.append(line)
            
            elif current_section == "examples":
                doc.examples.append(section.strip())
    
    def _build_signature(self, doc: DocElement) -> str:
        """Build function signature string."""
        parts = []
        
        for param in doc.parameters:
            part = param.name
            if param.type_hint and self.config.include_type_hints:
                part += f": {param.type_hint}"
            if param.default:
                part += f" = {param.default}"
            parts.append(part)
        
        params_str = ", ".join(parts)
        
        sig = f"{'async ' if doc.is_async else ''}def {doc.name}({params_str})"
        
        if doc.returns and doc.returns.type_hint and self.config.include_type_hints:
            sig += f" -> {doc.returns.type_hint}"
        
        return sig


# ============================================
# Documentation Generators
# ============================================

class MarkdownGenerator:
    """Generate Markdown documentation."""
    
    def __init__(self, config: DocConfig = None):
        self.config = config or DocConfig()
    
    def generate_module(self, module: ModuleDoc) -> str:
        """Generate documentation for a module."""
        lines = [
            f"# {module.name}",
            "",
        ]
        
        if module.docstring:
            lines.append(module.docstring)
            lines.append("")
        
        # Table of contents
        classes = [e for e in module.elements if e.doc_type == DocType.CLASS]
        functions = [e for e in module.elements if e.doc_type == DocType.FUNCTION]
        constants = [e for e in module.elements if e.doc_type == DocType.CONSTANT]
        
        if classes or functions:
            lines.append("## Table of Contents")
            lines.append("")
            
            if classes:
                lines.append("### Classes")
                for cls in classes:
                    lines.append(f"- [{cls.name}](#{cls.name.lower()})")
                lines.append("")
            
            if functions:
                lines.append("### Functions")
                for func in functions:
                    lines.append(f"- [{func.name}](#{func.name.lower()})")
                lines.append("")
        
        # Classes
        if classes:
            lines.append("## Classes")
            lines.append("")
            
            for cls in classes:
                lines.extend(self._generate_class(cls))
                lines.append("")
        
        # Functions
        if functions:
            lines.append("## Functions")
            lines.append("")
            
            for func in functions:
                lines.extend(self._generate_function(func))
                lines.append("")
        
        # Constants
        if constants:
            lines.append("## Constants")
            lines.append("")
            
            for const in constants:
                lines.append(f"### `{const.name}`")
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_class(self, cls: DocElement) -> list[str]:
        """Generate documentation for a class."""
        lines = [f"### {cls.name}"]
        
        if cls.bases:
            lines.append(f"*Inherits from: {', '.join(cls.bases)}*")
        
        lines.append("")
        
        if cls.docstring:
            lines.append(cls.docstring)
            lines.append("")
        
        # Attributes
        if cls.attributes:
            lines.append("#### Attributes")
            lines.append("")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for attr in cls.attributes:
                lines.append(f"| `{attr.name}` | `{attr.signature}` | |")
            lines.append("")
        
        # Methods
        if cls.methods:
            lines.append("#### Methods")
            lines.append("")
            
            for method in cls.methods:
                lines.extend(self._generate_function(method, level=5))
                lines.append("")
        
        return lines
    
    def _generate_function(self, func: DocElement, level: int = 4) -> list[str]:
        """Generate documentation for a function."""
        header = "#" * level
        lines = [f"{header} `{func.name}`"]
        lines.append("")
        
        # Signature
        if func.signature:
            lines.append("```python")
            lines.append(func.signature)
            lines.append("```")
            lines.append("")
        
        # Description
        if func.docstring:
            # Get first paragraph as description
            desc = func.docstring.split("\n\n")[0]
            lines.append(desc)
            lines.append("")
        
        # Parameters
        if func.parameters:
            lines.append("**Parameters:**")
            lines.append("")
            lines.append("| Name | Type | Required | Default | Description |")
            lines.append("|------|------|----------|---------|-------------|")
            for param in func.parameters:
                required = "Yes" if param.required else "No"
                default = f"`{param.default}`" if param.default else "-"
                lines.append(f"| `{param.name}` | `{param.type_hint or '-'}` | {required} | {default} | {param.description} |")
            lines.append("")
        
        # Returns
        if func.returns:
            lines.append("**Returns:**")
            lines.append("")
            ret_type = f"`{func.returns.type_hint}`" if func.returns.type_hint else ""
            lines.append(f"- {ret_type} {func.returns.description}")
            lines.append("")
        
        # Raises
        if func.raises:
            lines.append("**Raises:**")
            lines.append("")
            for exc in func.raises:
                lines.append(f"- {exc}")
            lines.append("")
        
        # Examples
        if func.examples and self.config.include_examples:
            lines.append("**Example:**")
            lines.append("")
            lines.append("```python")
            for example in func.examples:
                lines.append(example)
            lines.append("```")
            lines.append("")
        
        return lines
    
    def generate_api_docs(self, modules: list[ModuleDoc]) -> str:
        """Generate combined API documentation."""
        lines = [
            "# API Reference",
            "",
            f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## Modules",
            "",
        ]
        
        # Index
        for module in modules:
            lines.append(f"- [{module.name}](#{module.name.lower().replace('.', '')})")
        lines.append("")
        
        # Module documentation
        for module in modules:
            lines.append("---")
            lines.append("")
            lines.append(self.generate_module(module))
        
        return "\n".join(lines)


class HTMLGenerator:
    """Generate HTML documentation."""
    
    def __init__(self, config: DocConfig = None):
        self.config = config or DocConfig()
    
    def generate_module(self, module: ModuleDoc) -> str:
        """Generate HTML documentation for a module."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{module.name} - API Documentation</title>
    <style>
        :root {{
            --primary: #2196f3;
            --bg: #ffffff;
            --text: #333333;
            --code-bg: #f5f5f5;
            --border: #e0e0e0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: var(--bg);
            color: var(--text);
        }}
        h1 {{ color: var(--primary); border-bottom: 2px solid var(--primary); padding-bottom: 10px; }}
        h2 {{ color: var(--primary); margin-top: 40px; }}
        h3 {{ margin-top: 30px; }}
        code {{ background: var(--code-bg); padding: 2px 6px; border-radius: 3px; font-family: 'Fira Code', monospace; }}
        pre {{ background: var(--code-bg); padding: 15px; border-radius: 5px; overflow-x: auto; }}
        pre code {{ padding: 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid var(--border); padding: 10px; text-align: left; }}
        th {{ background: var(--code-bg); }}
        .signature {{ background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .docstring {{ margin: 15px 0; }}
        .toc {{ background: var(--code-bg); padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .toc ul {{ margin: 0; padding-left: 20px; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; margin-left: 5px; }}
        .badge-async {{ background: #e8f5e9; color: #2e7d32; }}
        .badge-static {{ background: #fff3e0; color: #e65100; }}
        .badge-property {{ background: #f3e5f5; color: #7b1fa2; }}
    </style>
</head>
<body>
    <h1>{module.name}</h1>
    <p><code>{module.path}</code></p>
"""
        
        if module.docstring:
            html += f'    <div class="docstring">{self._escape_html(module.docstring)}</div>\n'
        
        # Table of contents
        classes = [e for e in module.elements if e.doc_type == DocType.CLASS]
        functions = [e for e in module.elements if e.doc_type == DocType.FUNCTION]
        
        if classes or functions:
            html += '    <div class="toc"><h2>Contents</h2><ul>\n'
            for cls in classes:
                html += f'        <li><a href="#{cls.name}">{cls.name}</a> (class)</li>\n'
            for func in functions:
                html += f'        <li><a href="#{func.name}">{func.name}</a> (function)</li>\n'
            html += '    </ul></div>\n'
        
        # Classes
        for cls in classes:
            html += self._generate_class_html(cls)
        
        # Functions
        if functions:
            html += '    <h2>Functions</h2>\n'
            for func in functions:
                html += self._generate_function_html(func)
        
        html += """</body>
</html>"""
        
        return html
    
    def _generate_class_html(self, cls: DocElement) -> str:
        """Generate HTML for a class."""
        html = f'    <h2 id="{cls.name}">{cls.name}</h2>\n'
        
        if cls.bases:
            html += f'    <p><em>Inherits from: {", ".join(cls.bases)}</em></p>\n'
        
        if cls.docstring:
            html += f'    <div class="docstring">{self._escape_html(cls.docstring)}</div>\n'
        
        if cls.methods:
            html += '    <h3>Methods</h3>\n'
            for method in cls.methods:
                html += self._generate_function_html(method)
        
        return html
    
    def _generate_function_html(self, func: DocElement) -> str:
        """Generate HTML for a function."""
        badges = ""
        if func.is_async:
            badges += '<span class="badge badge-async">async</span>'
        if func.is_static:
            badges += '<span class="badge badge-static">static</span>'
        if func.is_property:
            badges += '<span class="badge badge-property">property</span>'
        
        html = f'    <h4 id="{func.name}">{func.name}{badges}</h4>\n'
        
        if func.signature:
            html += f'    <div class="signature"><code>{self._escape_html(func.signature)}</code></div>\n'
        
        if func.docstring:
            desc = func.docstring.split("\n\n")[0]
            html += f'    <p>{self._escape_html(desc)}</p>\n'
        
        if func.parameters:
            html += '    <h5>Parameters</h5>\n'
            html += '    <table>\n'
            html += '        <tr><th>Name</th><th>Type</th><th>Required</th><th>Default</th><th>Description</th></tr>\n'
            for param in func.parameters:
                required = "Yes" if param.required else "No"
                default = f"<code>{param.default}</code>" if param.default else "-"
                html += f'        <tr><td><code>{param.name}</code></td><td><code>{param.type_hint or "-"}</code></td><td>{required}</td><td>{default}</td><td>{param.description}</td></tr>\n'
            html += '    </table>\n'
        
        if func.returns:
            html += '    <h5>Returns</h5>\n'
            html += f'    <p><code>{func.returns.type_hint}</code> - {func.returns.description}</p>\n'
        
        return html
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )


# ============================================
# Auto Documentation Manager
# ============================================

class AutoDocGenerator:
    """Main auto-documentation generator."""
    
    def __init__(self, config: DocConfig = None):
        self.config = config or DocConfig()
        self._parser = CodeParser(self.config)
        
        self._generators = {
            DocFormat.MARKDOWN: MarkdownGenerator(self.config),
            DocFormat.HTML: HTMLGenerator(self.config),
        }
    
    async def generate_module_docs(
        self,
        file_path: str,
        format: DocFormat = None,
    ) -> str:
        """Generate documentation for a single module."""
        format = format or self.config.format
        
        module_doc = self._parser.parse_file(file_path)
        
        generator = self._generators.get(format)
        if not generator:
            generator = MarkdownGenerator(self.config)
        
        content = generator.generate_module(module_doc)
        
        # AI enhancement if enabled
        if self.config.use_ai_enhancement:
            content = await self._enhance_with_ai(content)
        
        return content
    
    async def generate_api_docs(
        self,
        directory: str,
        format: DocFormat = None,
        recursive: bool = True,
    ) -> str:
        """Generate API documentation for all modules in a directory."""
        format = format or self.config.format
        
        modules = []
        path = Path(directory)
        
        if recursive:
            files = path.rglob("*.py")
        else:
            files = path.glob("*.py")
        
        for file_path in files:
            if file_path.name.startswith("_") and not file_path.name == "__init__.py":
                continue
            
            try:
                module_doc = self._parser.parse_file(str(file_path))
                if module_doc.elements:  # Only include modules with documented elements
                    modules.append(module_doc)
            except Exception as e:
                logger.warning(f"Failed to parse {file_path}: {e}")
        
        # Sort modules by name
        modules.sort(key=lambda m: m.name)
        
        generator = self._generators.get(format, MarkdownGenerator(self.config))
        
        if hasattr(generator, 'generate_api_docs'):
            return generator.generate_api_docs(modules)
        else:
            # Fallback: concatenate module docs
            docs = []
            for module in modules:
                docs.append(generator.generate_module(module))
            return "\n\n---\n\n".join(docs)
    
    async def generate_readme(
        self,
        project_dir: str,
        template: str = None,
    ) -> str:
        """Generate a README file for the project."""
        path = Path(project_dir)
        
        # Gather project information
        project_name = path.name
        
        # Check for existing README
        existing_readme = ""
        readme_path = path / "README.md"
        if readme_path.exists():
            existing_readme = readme_path.read_text(encoding="utf-8")
        
        # Check for package info
        setup_py = path / "setup.py"
        pyproject = path / "pyproject.toml"
        
        description = ""
        if pyproject.exists():
            content = pyproject.read_text()
            match = re.search(r'description\s*=\s*"([^"]+)"', content)
            if match:
                description = match.group(1)
        
        # Check for requirements
        requirements = []
        req_file = path / "requirements.txt"
        if req_file.exists():
            requirements = [
                line.strip() for line in req_file.read_text().split("\n")
                if line.strip() and not line.startswith("#")
            ]
        
        # Build README
        sections = []
        
        # Header
        sections.append(f"# {project_name}")
        sections.append("")
        
        if description:
            sections.append(description)
            sections.append("")
        
        # Installation
        if "installation" in self.config.readme_sections:
            sections.append("## Installation")
            sections.append("")
            sections.append("```bash")
            sections.append(f"pip install {project_name}")
            sections.append("```")
            sections.append("")
            
            if requirements:
                sections.append("### Requirements")
                sections.append("")
                for req in requirements[:10]:
                    sections.append(f"- {req}")
                if len(requirements) > 10:
                    sections.append(f"- ... and {len(requirements) - 10} more")
                sections.append("")
        
        # Usage
        if "usage" in self.config.readme_sections:
            sections.append("## Usage")
            sections.append("")
            sections.append("```python")
            sections.append(f"import {project_name}")
            sections.append("```")
            sections.append("")
        
        # API (brief)
        if "api" in self.config.readme_sections:
            # Find main modules
            src_dir = path / "src"
            if not src_dir.exists():
                src_dir = path
            
            modules = list(src_dir.glob("*.py"))[:5]
            
            if modules:
                sections.append("## API Overview")
                sections.append("")
                
                for module_path in modules:
                    if module_path.name.startswith("_"):
                        continue
                    try:
                        module_doc = self._parser.parse_file(str(module_path))
                        if module_doc.elements:
                            sections.append(f"### {module_doc.name}")
                            if module_doc.docstring:
                                first_line = module_doc.docstring.split("\n")[0]
                                sections.append(first_line)
                            sections.append("")
                    except:
                        pass
        
        # License
        if "license" in self.config.readme_sections:
            license_file = path / "LICENSE"
            if license_file.exists():
                sections.append("## License")
                sections.append("")
                sections.append("See [LICENSE](LICENSE) for details.")
                sections.append("")
        
        return "\n".join(sections)
    
    async def generate_to_file(
        self,
        source: str,
        output_path: str,
        format: DocFormat = None,
        doc_type: str = "module",
    ) -> str:
        """Generate documentation and write to file."""
        format = format or self.config.format
        
        if doc_type == "module":
            content = await self.generate_module_docs(source, format)
        elif doc_type == "api":
            content = await self.generate_api_docs(source, format)
        elif doc_type == "readme":
            content = await self.generate_readme(source)
        else:
            raise ValueError(f"Unknown doc_type: {doc_type}")
        
        # Write to file
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        
        logger.info(f"Documentation written to {output_path}")
        return str(output)
    
    async def _enhance_with_ai(self, content: str) -> str:
        """Enhance documentation using AI."""
        try:
            from .llm_providers import get_llm_manager
            
            llm = get_llm_manager()
            
            prompt = f"""Please review and enhance the following documentation.
Improve clarity, add missing details, and fix any issues.
Keep the same format (Markdown).

Documentation:
{content}

Enhanced documentation:"""
            
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
            )
            
            return response
            
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")
            return content


# ============================================
# Global Instance
# ============================================

_doc_generator: Optional[AutoDocGenerator] = None


def get_doc_generator(config: DocConfig = None) -> AutoDocGenerator:
    """Get the global documentation generator instance."""
    global _doc_generator
    
    if _doc_generator is None:
        _doc_generator = AutoDocGenerator(config)
        logger.info("Auto-documentation generator initialized")
    
    return _doc_generator


def reset_doc_generator() -> None:
    """Reset the documentation generator instance."""
    global _doc_generator
    _doc_generator = None


__all__ = [
    # Types
    "DocFormat",
    "DocType",
    "DocParameter",
    "DocReturn",
    "DocElement",
    "ModuleDoc",
    "DocConfig",
    # Parser
    "CodeParser",
    # Generators
    "MarkdownGenerator",
    "HTMLGenerator",
    # Manager
    "AutoDocGenerator",
    "get_doc_generator",
    "reset_doc_generator",
]
