import ast
import sys
import os

REQUIRED_TAGS = ["[EXPLANATORY:", "[IDENTIFIER:"]
DIRECTIONAL_TAG = "[DIRECTIONAL:"

def check_docstring(node, file_path, requires_directional=False):
    docstring = ast.get_docstring(node)
    name = getattr(node, 'name', 'Module')

    if not docstring:
        return f"❌ {file_path}: '{name}' is missing a docstring entirely."

    for tag in REQUIRED_TAGS:
        if tag not in docstring:
            return f"❌ {file_path}: '{name}' is missing the {tag} ...] tag."

    if requires_directional and DIRECTIONAL_TAG not in docstring:
        return f"❌ {file_path}: '{name}' returns a value but is missing the {DIRECTIONAL_TAG} ...] tag."

    return None

def analyze_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=file_path)

    errors = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            err = check_docstring(node, file_path)
            if err: errors.append(err)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if function has a return statement
            class ReturnVisitor(ast.NodeVisitor):
                def __init__(self):
                    self.has_return = False
                def visit_Return(self, n):
                    if n.value is not None:
                        self.has_return = True
                def visit_FunctionDef(self, n):
                    pass
                def visit_AsyncFunctionDef(self, n):
                    pass

            visitor = ReturnVisitor()
            for child in node.body:
                visitor.visit(child)

            err = check_docstring(node, file_path, requires_directional=visitor.has_return)
            if err: errors.append(err)

    return errors

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "simulations"
    all_errors = []

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                all_errors.extend(analyze_file(os.path.join(root, file)))

    if all_errors:
        print("\n".join(all_errors))
        sys.exit(1)

    print("✅ All modules, classes, and functions comply with the Credon Semantic Taxonomy.")
    sys.exit(0)
