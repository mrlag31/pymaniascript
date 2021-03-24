from CppHeaderParser import CppHeader, CppParseError

NAMESPACE = '__NAMESPACE__'
__DOCH = None
__ENUM_WRONG_VALUES = ['*unused*', '(reserved)', 'XXX Null']
__DOCH_FILENAME = __file__[:-11] + 'doc.h'

def __compute_doch (filename=None):
    global __DOCH
    
    filename = filename if filename else __DOCH_FILENAME
    try:
        with open(filename, 'r') as f: data = f.read()
    except FileNotFoundError:
        print('\'doc.h\' has not been found. Please run \'python -m pymaniascript.doch <your TM2020 exe path>\'.')
        exit()
    
    for ewv in __ENUM_WRONG_VALUES: data = data.replace(f'{ewv},\n', '')
    data = data.replace('namespace ', f'class {NAMESPACE}')
    
    try:
        __DOCH = CppHeader(data, argType='string').classes
    except CppParseError as e:
        raise Exception(f'Exception while parsing file \'{filename}\': {e}')

def get_doch (filename=None):
    if __DOCH == None:
        __compute_doch(filename)
    return __DOCH