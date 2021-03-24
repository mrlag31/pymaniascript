from .parser import Parser

def compile (filepath, root_folder):
    return Parser(root_folder).parse_file(filepath)