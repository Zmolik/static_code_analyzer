import sys
import os
import re
import ast


class PEP8:

    def __init__(self, code: list):
        self.code = code
        self.issues = []
        self.blank_lines = 0

    def check_length(self, ln_num, line):
        if len(line) > 79:
            self.issues.append(f"Line {ln_num}: S001 Too Long")

    def check_indentation(self, ln_num, line):
        if line.startswith(' '):
            count = 0
            for char in line:
                if char == ' ':
                    count += 1
                else:
                    break
            if count % 4 != 0:
                self.issues.append(f"Line {ln_num}: S002 Indentation is not a multiple of four")

    def check_semicolon(self, ln_num, line):
        single_quote, quote, pound = 0, 0, 0
        for char in line:
            if char == '"':
                quote += 1
            elif char == "'":
                single_quote += 1
            elif char == '#':
                pound = 1
            elif char == ';':
                if quote % 2 == 0 and single_quote % 2 == 0:
                    if not pound:
                        self.issues.append(f"Line {ln_num}: S003 Unnecessary semicolon")
                        break

    def check_spaces_before_inline_comment(self, ln_num, line):
        ind = line.find('#')
        if ind > 1:
            if line[ind - 1] != ' ' or line[ind - 2] != ' ':
                self.issues.append(f"Line {ln_num}: S004 At least two spaces before inline comments required")

    def check_todo(self, ln_num, line):
        if '#' in line:
            if 'todo' in line and line.find('#') < line.find('todo'):
                self.issues.append(f"Line {ln_num}: S005 TODO found")
            elif 'TODO' in line and line.find('#') < line.find('TODO'):
                self.issues.append(f"Line {ln_num}: S005 TODO found")
            elif 'Todo' in line and line.find('#') < line.find('Todo'):
                self.issues.append(f"Line {ln_num}: S005 TODO found")

    def check_blank_lines(self, ln_num, line):
        if line != '\n' and self.blank_lines <= 2:
            self.blank_lines = 0
        elif self.blank_lines >= 3 and line != '\n':
            self.issues.append(f"Line {ln_num}: S006 More than two blank lines used before this line")
            self.blank_lines = 0
        elif line == '\n':
            self.blank_lines += 1

    def check_spaces_after_construction_name(self, ln_num, line):
        line = line.lstrip()
        if line.startswith('def'):
            if re.match('def [^ ]', line) is None:
                self.issues.append(f"Line {ln_num}: S007 Too many spaces after construction_name (def)")
        elif line.startswith('class'):
            if re.match('class [^ ]', line) is None:
                self.issues.append(f"Line {ln_num}: S007 Too many spaces after construction_name (class)")

    def check_class_camel_case(self, ln_num, line):
        line = line.lstrip()
        regexp_1 = 'class *[A-Z][a-zA-Z0-9]*:'
        regexp_2 = r'class *[A-Z][a-zA-Z0-9]*\('
        if line.startswith('class'):
            if re.match(regexp_1, line) is None and re.match(regexp_2, line) is None:
                self.issues.append(f"Line {ln_num}: S008 Class name should use CamelCase")

    def check_def_snake_case(self, ln_num, line):
        line = line.lstrip()
        regexp = r'def *_{0,2}[a-z][a-z0-9_]*_{0,2}\('
        if line.startswith('def'):
            if re.match(regexp, line) is None:
                self.issues.append(f"Line {ln_num}: S009 Function name should use snake_case")

    def output_issues(self):
        return self.issues

    def run_check(self):
        for ln_num, line in enumerate(self.code, 1):
            self.check_length(ln_num, line)
            self.check_indentation(ln_num, line)
            self.check_semicolon(ln_num, line)
            self.check_spaces_before_inline_comment(ln_num, line)
            self.check_todo(ln_num, line)
            self.check_blank_lines(ln_num, line)
            self.check_spaces_after_construction_name(ln_num, line)
            self.check_class_camel_case(ln_num, line)
            self.check_def_snake_case(ln_num, line)


class AstAnalyzer(ast.NodeVisitor):

    def __init__(self, tree):
        self.tree = tree
        self.issues = []
        self.mutables = set()
        self.arguments = set()

    def output_issues(self):
        return self.issues

    @staticmethod
    def check_args_vars_name(name):
        regexp = r'[a-z_]+[_a-z0-9]*$'
        if re.match(regexp, name) is None:
            return False                                # no match
        else:
            return True                                 # match

    def visit_FunctionDef(self, node):
        for argument in node.args.args:                 # prints raw strings of all arguments of all functions
            if not self.check_args_vars_name(argument.arg):
                if node.lineno not in self.arguments:
                    self.issues.append(f"Line {node.lineno}: S010 Argument name {argument.arg} should be snake_case")
                    self.arguments.add(node.lineno)

        for body_node in node.body:
            if isinstance(body_node, ast.Assign):
                for target in body_node.targets:
                    if isinstance(target, ast.Attribute):
                        if not self.check_args_vars_name(target.attr):
                            self.issues.append(f"Line {target.lineno}: S011 Variable {target.attr} should be snake_case")
                    elif isinstance(target, ast.Name):
                        if not self.check_args_vars_name(target.id):
                            self.issues.append(f"Line {target.lineno}: S011 Variable {target.id} should be snake_case")

        for default in node.args.defaults:
            try:
                a = default.value
            except:
                if not isinstance(default, ast.Tuple):  # the only immutable object is tuple
                    if node.lineno not in self.mutables:
                        self.issues.append(f"Line {node.lineno}: S012 Default argument is mutable")
                        self.mutables.add(node.lineno)

    def run_check(self):
        self.visit(self.tree)


class StaticCodeAnalyzer:

    def __init__(self):
        self.path = None
        self.code = None
        self.tree = None

    @staticmethod
    def read_file(file_location: str) -> list:
        with open(file_location, 'r') as file:
            return file.readlines()

    @staticmethod
    def convert_file_to_ast(file_location):
        with open(file_location, 'r') as source:
            return ast.parse(source.read())

    def check_py_files_pep8(self):
        all_files = os.listdir(self.path)
        for file in all_files:
            if file.endswith('py'):
                path_to_file = os.path.join(self.path, file)
                self.check_file_pep8(path_to_file)

    def check_file_pep8(self, path_to_single_file):
        # check part of the possible mistakes without using AST
        self.code = self.read_file(path_to_single_file)
        pep8_obj = PEP8(self.code)
        pep8_obj.run_check()
        # check part of the possible mistakes with AST
        self.tree = self.convert_file_to_ast(path_to_single_file)
        ast_analyzer = AstAnalyzer(self.tree)
        ast_analyzer.run_check()
        # output all issues
        pep8_issues = pep8_obj.output_issues()
        ast_issues = ast_analyzer.output_issues()
        result = (pep8_issues + ast_issues)
        for issue in result:
            print(f'{path_to_single_file}: {issue}')

    def main(self):
        args = sys.argv  # python code_analyzer.py[0] directory-or-file[1]
        self.path = args[1]  # path can be to a single file or to a directory which contains files
        if os.path.isdir(self.path):
            self.check_py_files_pep8()
        else:
            self.check_file_pep8(self.path)


program = StaticCodeAnalyzer()
program.main()