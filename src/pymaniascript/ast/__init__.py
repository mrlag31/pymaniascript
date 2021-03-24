from pymaniascript.msobjects import *
from .report import FATAL_ERROR, ERROR, WARNING, reporter
from pymaniascript.scope import Scope

class Index:
    
    def __init__ (self, index, text):
        self.index = index
        self.ln = text.count('\n', 0, index) + 1
        self.col = index - text.rfind('\n', 0, index)
    
    def __str__ (self):
        return f'[{self.ln}, {self.col}]'

class ASTNode:
    
    def __init__ (self, children, p):
        first = p[0]
        last = p[-1]
        if isinstance(first, list): first = first[0]
        if isinstance(last , list): last  = last [0]
        self.children, self.start, self.end = children, first.start, last.end
        
        self.reports = list()
        for child in children:
            self.reports.extend(child.reports)
    
    def str (self, i=0, data=None):
        res = ''
        
        if data != None:
            res += '| '*i + f'+ {self.start} - {self.end} {self.__class__.__name__}: {repr(data)}\n'
        else:
            res += '| '*i + f'+ {self.start} - {self.end} {self.__class__.__name__}\n'
        
        for child in self.children:
            res += f'{child.str(i+1)}\n'
        
        return res[:-1]
    
    def __str__ (self):
        return self.str()
    
# ---

class ASTTerminal (ASTNode):
    
    def __init__ (self, p, content):
        super().__init__(list(), [p])
        self.content = content
    
    def str (self, i=0, data=None):
        return super().str(i=i, data=data or self.content)

class ASTTerminalValue (ASTTerminal):
    
    def __init__(self, p, value):
        super().__init__(p, value)
        self.value = value
        self.type = self.value.type if hasattr(self.value, 'type') else None

class ASTTerminalEmpty (ASTTerminal):
    
    class Empty:
        
        def __init__ (self, pos):
            self.start, self.end = pos, pos
    
    def __init__ (self, last_token_end):
        super().__init__(ASTTerminalEmpty.Empty(last_token_end), None)
    
EMPTY = ASTTerminalEmpty(Index(0, ''))
ASTTerminalEmpty.EMPTY = EMPTY
del EMPTY

# ---

class ASTVector (ASTNode):
    
    def __init__ (self, p, elements, reporter):
        super().__init__(elements, p)
        types = [element.type for element in elements]
        self.type = VOID
        
        if types == [INTEGER, INTEGER]:
            self.type = INT2
        elif types == [INTEGER, INTEGER, INTEGER]:
            self.type = INT3
        elif types[0] in [INTEGER, REAL] and types[1] in [INTEGER, REAL]:
            if len(types) == 2:
                self.type = VEC2
            elif types[2] in [INTEGER, REAL]:
                self.type = VEC3
        
        if self.type == VOID:
            self.reports.append(reporter(
                ERROR, self, f'Invalid types in vector.'
            ))
        
        self.value = MSValue('@VECTOR', self.type)

# ---

class ASTExpressionBinaryOperation (ASTNode):
    
    def __init__(self, p, left, operation, right, reporter):
        super().__init__([left, operation, right], p)
        self.type = VOID
        
        self.left, self.operation, self.right = left, operation, right
        
        op = operation.content
        if op in ['+', '-']:
            mapping = {
                (INTEGER, INTEGER): INTEGER,
                (REAL, INTEGER)   : REAL,
                (INTEGER, REAL)   : REAL,
                (REAL, REAL)      : REAL,
                (INT2, INT2)      : INT2,
                (VEC2, INT2)      : VEC2,
                (INT2, VEC2)      : VEC2,
                (VEC2, VEC2)      : VEC2,
                (INT3, INT3)      : INT3,
                (VEC3, INT3)      : VEC3,
                (INT3, VEC3)      : VEC3,
                (VEC3, VEC3)      : VEC3,
            }
            types = (left.type, right.type)
            self.type = mapping.get(types, VOID)
        elif op == '*':
            mapping = {
                (INTEGER, INTEGER): INTEGER,
                (REAL, INTEGER)   : REAL,
                (INTEGER, REAL)   : REAL,
                (REAL, REAL)      : REAL,
                (INTEGER, INT2)   : INT2,
                (REAL, INT2)      : VEC2,
                (INT2, INTEGER)   : INT2,
                (INT2, REAL)      : VEC2,
                (INTEGER, VEC2)   : VEC2,
                (REAL, VEC2)      : VEC2,
                (VEC2, INTEGER)   : VEC2,
                (VEC2, REAL)      : VEC2,
                (INTEGER, INT3)   : INT3,
                (REAL, INT3)      : VEC3,
                (INT3, INTEGER)   : INT3,
                (INT3, REAL)      : VEC3,
                (INTEGER, VEC3)   : VEC3,
                (REAL, VEC3)      : VEC3,
                (VEC3, INTEGER)   : VEC3,
                (VEC3, REAL)      : VEC3,
            }
            types = (left.type, right.type)
            self.type = mapping.get(types, VOID)
        elif op == '/':
            mapping = {
                (INTEGER, INTEGER): INTEGER,
                (REAL, INTEGER)   : REAL,
                (INTEGER, REAL)   : REAL,
                (REAL, REAL)      : REAL,
            }
            types = (left.type, right.type)
            self.type = mapping.get(types, VOID)
        elif op == '%':
            if left.type == INTEGER and right.type == INTEGER:
                self.type = INTEGER
        elif op == '^':
            if left.type == TEXT or right.type == TEXT:
                self.type = TEXT
        elif op in ['>', '<', '>=', '<=']:
            valid = [
                (INTEGER, INTEGER),
                (REAL, INTEGER),
                (INTEGER, REAL),
                (REAL, REAL)
            ]
            types = (left.type, right.type)
            if types in valid:
                self.type = BOOLEAN
        elif op in ['==', '!=']:
            if left.type.is_type(right.type) or right.type.is_type(left.type):
                self.type = BOOLEAN
        elif op in ['&&', '||']:
            if left.type == BOOLEAN and right.type == BOOLEAN:
                self.type = BOOLEAN
        elif op == 'is':
            if isinstance(left.type, MSClass):
                self.type = BOOLEAN
        
        if self.type == VOID:
            self.reports.append(reporter(
                ERROR, self, f'Operation \'{op}\' on incompatible type.'
            ))
        
        self.value = MSValue('@BINOP', self.type, True)

class ASTExpressionUnaryOperation (ASTNode):
    
    def __init__(self, p, operation, right, reporter):
        super().__init__([operation, right], p)
        self.type = VOID
        
        self.operation, self.right = operation, right
        
        op = operation.content
        if op == '-':
            valid = [INTEGER, REAL, INT2, VEC2, INT3, VEC3]
            if right.type in valid:
                self.type = right.type
        elif op == '!':
            if right.type == BOOLEAN:
                self.type = right.type
        
        if self.type == VOID:
            self.reports.append(reporter(
                ERROR, self, f'Operation \'{op}\' on incompatible type.'
            ))
        
        self.value = MSValue('@UNIOP', self.type, True)

# ---

class ASTFunctionCall (ASTNode):
    
    def __init__(self, p, function, arguments, reporter):
        super().__init__([function, *arguments], p)
        
        fobj = function.value
        sign = fobj.valid_signature([arg.type for arg in arguments])
        if sign == None:
            self.reports.append(reporter(
                ERROR, self, f'Invalid arguments for function \'{fobj.name}\''
            ))
            self.type = VOID
        else:
            self.type = sign
        
        self.value = MSValue('@FUNCRESULT', self.type, True)

# ---

class ASTArray (ASTNode):
    
    def __init__(self, p, array, index, reporter):
        super().__init__([array, index], p)
        
        if not isinstance(array.type, MSArray):
            self.reports.append(reporter(
                ERROR, self, f'\'{array.value.name}\' is not an array.'
            ))
            self.type = VOID
        
        elif not index.type.is_type(array.type.keytype):
            self.reports.append(reporter(
                ERROR, self, f'Invalid index type. Expected \'{array.type.keytype.name}\' but got \'{index.type.name}\''
            ))
            self.type = array.type.elemtype
        
        else:
            self.type = array.type.elemtype
        
        self.value = MSValue('@ARRAY', self.type)

# ---

class ASTDot (ASTNode):
    
    def __init__(self, p, parent, child):
        super().__init__([parent, child], p)
        
        self.parent, self.value = parent, child.value
        self.type = self.value.type if hasattr(self.value, 'type') else None

class ASTNamespace (ASTNode):
    
    def __init__ (self, p, namespace, obj):
        super().__init__([namespace, obj], p)
        
        self.namespace, self.value = namespace.value, obj.value
        self.type = self.value.type if hasattr(self.value, 'type') else None

class ASTEnum (ASTNode):
    
    def __init__ (self, p, parent, enum_value):
        super().__init__([parent, enum_value], p)
        
        self.parent, self.value = parent, enum_value.value
        self.type = self.parent.value

# ---

class ASTKeyElem (ASTNode):
    
    def __init__(self, p, elem, key):
        super().__init__([key, elem], p)
        self.key, self.elem = key, elem

class ASTArrayDef (ASTNode):
    
    def __init__(self, p, elements, reporter):
        super().__init__(elements, p)
        self.type = None
        
        if len(elements) == 0:
            self.type = get_array(ANY, ANY)
        else:
            
            if isinstance(elements[0], ASTKeyElem):
                keytypes, elemtypes = [], []
                for elem_key in elements:
                    keytypes.append(elem_key.key.type)
                    elemtypes.append(elem_key.elem.type)
                
                key_no_any = [keytype for keytype in keytypes if not keytype.has_any()]
                key_no_null = [keytype for keytype in key_no_any if not keytype.has_null()]
                
                elem_no_any = [elemtype for elemtype in elemtypes if not elemtype.has_any()]
                elem_no_null = [elemtype for elemtype in elem_no_any if not elemtype.has_null()]
                
                if len(key_no_null) != 0:
                    keytype = key_no_null[0]
                elif len(key_no_any) != 0:
                    keytype = key_no_any[0]
                else:
                    keytype = keytypes[0]
                
                if len(elem_no_null) != 0:
                    elemtype = elem_no_null[0]
                elif len(elem_no_any) != 0:
                    elemtype = elem_no_any[0]
                else:
                    elemtype = elemtypes[0]
                
                key_valid = [ktype.is_type(keytype) for ktype in keytypes]
                if False in key_valid:
                    self.reports.append(reporter(
                        ERROR, self, f'Every key must have type {elemtype.name}.'
                    ))
                
                elem_valid = [etype.is_type(elemtype) for etype in elemtypes]
                if False in elem_valid:
                    self.reports.append(reporter(
                        ERROR, self, f'Every element must have type {elemtype.name}.'
                    ))
                
                self.type = get_array(elemtype, keytype)
            
            else:
                elemtypes = []
                for elem in elements:
                    elemtypes.append(elem.type)
                
                elem_no_any = [elemtype for elemtype in elemtypes if not elemtype.has_any()]
                elem_no_null = [elemtype for elemtype in elem_no_any if not elemtype.has_null()]
                
                if len(elem_no_null) != 0:
                    elemtype = elem_no_null[0]
                elif len(elem_no_any) != 0:
                    elemtype = elem_no_any[0]
                else:
                    elemtype = elemtypes[0]
                
                elem_valid = [etype.is_type(elemtype) for etype in elemtypes]
                if False in elem_valid:
                    self.reports.append(reporter(
                        ERROR, self, f'Every element must have type {elemtype.name}.'
                    ))
                
                self.type = get_array(elemtype)
        
        if self.type == None: self.type = VOID
        
        if isinstance(self.type, MSArray) and self.type.associative == True and isinstance(self.type.keytype, MSArray):
            self.reports.append(reporter(
                ERROR, self, f'Arrays cannot be indexers.'
            ))
            
        
        self.value = MSValue('@ARRAYDEF', self.type, True)

# ---

class ASTTypeArray (ASTNode):
    
    def __init__ (self, p, elemtype, keytype):
        children = [elemtype] + ([keytype] if keytype != None else [])
        super().__init__(children, p)
        
        if keytype == None:
            self.value = get_array(elemtype.value)
        else:
            self.value = get_array(elemtype.value, keytype.value)

# ---

class ASTDeclare (ASTNode):
    
    def __init__ (self, p, mode, type, name, _as, _for, assign, value, reporter, glob=False):
        super().__init__([mode, type, name, _as, _for, assign, value], p)
        
        self.mode   = None if isinstance(mode  , ASTTerminalEmpty) else mode.content
        self.type   = None if isinstance(type  , ASTTerminalEmpty) else type.value
        self.name   = name.content
        self._as    = None if isinstance(_as   , ASTTerminalEmpty) else _as.content
        self._for   = None if isinstance(_for  , ASTTerminalEmpty) else _for
        self.assign = None if isinstance(assign, ASTTerminalEmpty) else assign
        self._value = None if isinstance(value , ASTTerminalEmpty) else value.value
        
        if self._as != None:
            self.name = self._as
        
        if glob == True and self._value != None:
            self.reports.append(reporter(
                ERROR, self, f'Global variables have no initial value.'
            ))
                   
        if self.type == None and (self._value == None or value.type.has_any() or value.type.has_null()):
            self.reports.append(reporter(
                ERROR, self, f'Unable to determine type.'
            ))
            self.type = VOID
        elif self.type != None and self._value != None and not self._value.is_type(self.type):
            self.reports.append(reporter(
                ERROR, self, f'Incompatible types in declare.'
            ))
        elif self.type == None:
            self.type = self._value.type
        
        if self._for != None and not isinstance(self._for.type, MSClass):
            self.reports.append(reporter(
                ERROR, self, f'Declare \'for\' requires a class.'
            ))
        
        def valid_type (root):
            if root == VOID:
                self.reports.append(reporter(
                    ERROR, self, f'Invalid type in declaration.'
                ))
            elif isinstance(root, MSArray):
                valid_type(root.elemtype)
        valid_type(self.type)
        
        if glob == True and not self.name.startswith('G_'):
            self.reports.append(reporter(
                WARNING, self, f'Global varibale \'{self.name}\' should start with \'G_\''
            ))
        
        if self.mode == 'persistent' and not self.name.startswith('P_') and not self.name.startswith('Persistent_'):
            self.reports.append(reporter(
                WARNING, self, f'Persistent varibale \'{self.name}\' should start with \'P_\' or \'Persistent_\''
            ))
        
        if (self.mode == 'netread' or self.mode == 'netwrite') and not self.name.startswith('Net_'):
            self.reports.append(reporter(
                WARNING, self, f'Net varibale \'{self.name}\' should start with \'Net_\''
            ))
        
        self.value = MSValue(self.name, self.type)

# ---

class ASTBlock (ASTNode):
    
    def __init__ (self, p, statements):
        super().__init__(statements, p)
        self.statements = statements

class ASTFor (ASTNode):
    
    def __init__(self, p, iterator, start, end, step, block, reporter):
        super().__init__([iterator, start, end, step, block], p)
        
        self.iterator, self._start, self._end, self.step, self.block = iterator, start, end, step, block
        
        if self._start.type != INTEGER:
            self.reports.append(reporter(
                ERROR, self, f'Start must be an integer.'
            ))
        if self._end.type != INTEGER:
            self.reports.append(reporter(
                ERROR, self, f'End must be an integer.'
            ))
        if not isinstance(self.step, ASTTerminalEmpty) and self.step.type != INTEGER:
            self.reports.append(reporter(
                ERROR, self, f'Step must be an integer.'
            ))

class ASTForEach (ASTNode):
    
    def __init__ (self, p, iterator, array, block):
        super().__init__([iterator, array, block], p)
        
        self.iterator, self.array, self.block = iterator, array, block

class ASTIfElse (ASTNode):
    
    def __init__ (self, p, condition, ifblock, elseblock, reporter):
        super().__init__([condition, ifblock, elseblock], p)
        
        self.condition, self.ifblock, self.elseblock = condition, ifblock, elseblock
        if self.condition.type != BOOLEAN:
            self.reports.append(reporter(
                ERROR, self, f'Condition must be a boolean.'
            ))

class ASTWhile (ASTNode):
    
    def __init__ (self, p, condition, block, reporter):
        super().__init__([condition, block], p)
        
        self.condition, self.block = condition, block
        if self.condition.type != BOOLEAN:
            self.reports.append(reporter(
                ERROR, self, f'Condition must be a boolean.'
            ))

# ---

class ASTStructAssign (ASTNode):
    
    def __init__ (self, p, name, value):
        super().__init__([name, value], p)
        self.name = name.content
        self.value, self.type = value, value.type

class ASTStructCall (ASTNode):
    
    def __init__ (self, p, struct, assigns, reporter):
        super().__init__([struct, *assigns], p)
        
        self.struct = struct.value
        self.type = self.struct
        assigns_test = list()
        
        for assign in assigns:
            if assign.name in assigns_test:
                self.reports.append(reporter(
                    ERROR, self, f'Attribute \'{assign.name}\' set up multiple times.'
                ))
            
            struct_val = self.struct.get_attribute(assign.name)
            if struct_val == None:
                self.reports.append(reporter(
                    ERROR, self, f'Struct \'{self.struct.name}\' has no attribute \'{assign.name}\'.'
                ))
            
            if not assign.type.is_type(struct_val.type):
                self.reports.append(reporter(
                    ERROR, self, f'\'{assign.name}\' has wrong type. Expected \'{struct_val.type.name}\' but got \'{assign.type.name}\'.'
                ))
            
            assigns_test.append(assign.name)
        
        self.value = MSValue('@STRUCTCALL', self.struct, True)

# ---

class ASTSwitch (ASTNode):
    
    def __init__ (self, p, expression, cases, default, mode, reporter):
        super().__init__([expression, *cases, default], p)
        self.expression, self.cases, self.default = expression, cases, default
        self.mode = mode
        
        if mode == 0:
            type = self.expression.type
            for case in cases:
                for value in case.values:
                    if type != value.type:
                        self.reports.append(reporter(
                            ERROR, self, f'Wrong type in case. Found \'{value.type.name}\' instead of \'{type.name}\'.'
                        ))
        elif mode == 1:
            if not isinstance(self.expression.type, MSClass):
                self.reports.append(reporter(
                    ERROR, self, f'\'{self.expression.value.name}\' must be a class type.'
                ))

class ASTCase (ASTNode):
    
    def __init__ (self, p, values, block):
        super().__init__([*values, block], p)
        self.values = [value.value for value in values]
        self.block = block

class ASTDefault (ASTCase):
    
    def __init__ (self, p, block):
        super().__init__(p, [], block)

# ---

class ASTLabelCall (ASTNode):
    
    def __init__ (self, p, name, mode):
        super().__init__([name, mode], p)
        self.name = name.content
        self.mode = mode.content[0]

# ---

class ASTAssign (ASTNode):
    
    def __init__ (self, p, receiver, assign, value, reporter):
        super().__init__([receiver, assign, value], p)
        self.receiver, self.assign, self.value = receiver, assign, value
        
        if receiver.value.const:
            self.reports.append(reporter(
                ERROR, self, f'Trying to change \'{self.receiver.value.name}\' which is constant.'
            ))
        
        def wrong_type ():
            self.reports.append(reporter(
                ERROR, self, f'Setting \'{self.receiver.value.name}\' with incompatible types or operation.'
            ))
        
        op = assign.content
        if op == '=':
            if not ( receiver.type.is_type(value.type) or value.type.is_type(receiver.type) ):
                wrong_type()
        elif op == '<=>':
            if not ( isinstance(receiver.type, MSClass) and isinstance(value.type, MSClass) ):
                wrong_type()
        elif op in ['+=', '-=']:
            mapping = {
                (INTEGER, INTEGER),
                (REAL, INTEGER),
                (INTEGER, REAL),
                (REAL, REAL),
                (INT2, INT2),
                (VEC2, INT2),
                (INT2, VEC2),
                (VEC2, VEC2),
                (INT3, INT3),
                (VEC3, INT3),
                (INT3, VEC3),
                (VEC3, VEC3),
            }
            if (receiver.type, value.type) not in mapping:
                wrong_type()
        elif op == '*=':
            mapping = {
                (INTEGER, INTEGER),
                (REAL, INTEGER),
                (INTEGER, REAL),
                (REAL, REAL),
                (INT2, INTEGER),
                (VEC2, INTEGER),
                (VEC2, REAL),
                (INT3, INTEGER),
                (VEC3, INTEGER),
                (VEC3, REAL),
            }
            if (receiver.type, value.type) not in mapping:
                wrong_type()
        elif op == '/=':
            mapping = {
                (INTEGER, INTEGER),
                (REAL, INTEGER),
                (REAL, REAL),
            }
            if (receiver.type, value.type) not in mapping:
                wrong_type()
        elif op == '%=':
            if not (receiver.type == INTEGER and value.type == INTEGER):
                wrong_type()
        elif op == '^=':
            if not receiver.type == TEXT:
                wrong_type()

# ---

class ASTYield (ASTNode):
    
    def __init__(self, p):
        super().__init__([], p)

class ASTContinue (ASTNode):
    
    def __init__(self, p):
        super().__init__([], p)

class ASTBreak (ASTNode):
    
    def __init__(self, p):
        super().__init__([], p)

class ASTReturn (ASTNode):
    
    def __init__(self, p, value):
        super().__init__([value], p)
        self.value = value.value

# ---

class ASTInterpolatedString (ASTNode):
    
    def __init__ (self, p, elements):
        super().__init__(elements, p)
        self.elements = elements
        
        self.value = MSValue('@INTERPSTRING', TEXT, True)
        self.type = TEXT

# ---

class ASTFunctionDefinition (ASTNode):
    
    def __init__ (self, p, type, name, args, block, reporter, main=False):
        children = [type, name, *args, block] if not main else [name, *args, block]
        super().__init__(children, p)
        
        self.type = type.value if not main else VOID
        self.name = name.content
        self.block, self.args = block, [(argtype.value, argname.content) for argtype, argname in zip(args[::2], args[1::2])]
        
        for _, argname in self.args:
            if not argname.startswith('_'):
                self.reports.append(reporter(
                    WARNING, self, f'Argument \'{argname}\' should start with \'_\''
                ))
        
        def return_check (root):
            v = False
            
            if isinstance(root, ASTBlock):
                for statement in root.statements:
                    v |= return_check(statement)
            elif isinstance(root, (ASTWhile, ASTFor, ASTForEach)):
                v |= return_check(root.block)
            elif isinstance(root, ASTIfElse):
                v |= return_check(root.ifblock)
                v |= return_check(root.elseblock)
            elif isinstance(root, ASTSwitch):
                for case in root.cases:
                    v |= return_check(case.block)
                v |= return_check(root.default)
            elif isinstance(root, ASTReturn):
                v = True
                if not root.value.is_type(self.type):
                    self.reports.append(reporter(
                        ERROR, self, f'Wrong return type.'
                    ))
            return v
        return_found = return_check(self.block)
        
        def valid_type (root):
            if root == VOID:
                self.reports.append(reporter(
                    ERROR, self, f'Invalid type in arguments.'
                ))
            elif isinstance(root, MSArray):
                valid_type(root.elemtype)
        
        for arg in self.args:
            valid_type(arg[0])
        
        if self.type != VOID:
            valid_type(self.type)
        
        if return_found == False and self.type != VOID:
            self.reports.append(reporter(
                ERROR, self, f'Function \'{self.name}\' must return something.'
            ))

class ASTMain (ASTFunctionDefinition):
    
    def __init__(self, p, void_type, name, block):
        super().__init__(p, void_type, name, [], block, True)

class ASTLabelDef (ASTNode):
    
    def __init__ (self, p, name, block):
        super().__init__([name, block], p)
        self.name, self.block = name.content, block
        self.value = MSLabel(self.name)
        self.reports = list()

# ---

class ASTProg (ASTNode):
    
    def __init__ (self, p, directives, definitions, main, scope, reporter):
        super().__init__([*directives, *definitions, main], p)
        self.directives, self.definitions, self.main = directives, definitions, main
        self.scope = scope
        
        directives_counter = { root_type: 0 for root_type in [ASTDirectiveConst  , ASTDirectiveConstFromInclude ,
                                                              ASTDirectiveStruct , ASTDirectiveStructFromInclude,
                                                              ASTDirectiveInclude, ASTDirectiveRequireContext,
                                                              ASTDirectiveExtends, ASTDirectiveSetting,
                                                              ASTDirectiveCommand] }
        for directive in self.directives:
            directives_counter[type(directive)] += 1
        directives_counter[ASTDirectiveConst]  += directives_counter[ASTDirectiveConstFromInclude]
        directives_counter[ASTDirectiveStruct] += directives_counter[ASTDirectiveStructFromInclude]
        
        if directives_counter[ASTDirectiveExtends] >= 2:
            self.reports.append(reporter(
                ERROR, self, f'There must be at most one \'#Extends\'.'
            ))
        
        if directives_counter[ASTDirectiveExtends] >= 1 and isinstance(self.main, ASTMain):
            self.reports.append(reporter(
                ERROR, self, f'Scripts with \'#Extends\' cannot have a \'main\'.'
            ))

class ASTProgError (ASTProg):
    
    def __init__ (self, error_msg, reporter, offender=None):
        super().__init__([ASTTerminalEmpty.EMPTY], [], [], ASTTerminalEmpty.EMPTY, Scope(), reporter)
        offender = offender or self
        self.reports.append(reporter(FATAL_ERROR, offender, error_msg))
        
# ---

class ASTDirectiveConst (ASTNode):
    
    def __init__ (self, p, name, value):
        super().__init__([name, value], p)
        self.name = name.content
        self.value = MSValue(self.name, value.type, True)

class ASTDirectiveConstFromInclude (ASTNode):
    
    def __init__ (self, p, obj, name):
        super().__init__([obj, name], p)
        self.name = name.content
        self.value = MSValue(self.name, obj.value.type, True)

class ASTDirectiveStruct (ASTNode):
    
    def __init__ (self, p, name, args):
        super().__init__([name, *args], p)
        self.name = name.content
        struct_args = { argname.content: argtype.value for argtype, argname in zip(args[::2], args[1::2]) }
        self.struct = MSStruct(self.name, struct_args)

class ASTDirectiveStructFromInclude (ASTNode):
    
    def __init__ (self, p, obj, name):
        super().__init__([obj, name], p)
        self.name = name.content
        struct_args = { argname: argvalue.type for argname, argvalue in obj.value.attributes.items() }
        self.struct = MSStruct(self.name, struct_args)

class ASTDirectiveInclude (ASTNode):
    
    def __init__ (self, p, filepath, name, prog, reporter, from_doch=False):
        super().__init__([filepath, name], p)
        self.filepath = filepath.content
        self.name = name.content
        self.prog = prog if not from_doch else None
        self.include = MSInclude(self.name, self.prog.scope) if not from_doch else prog
        
        if self.prog != None and isinstance(self.prog.main, ASTMain):
            self.reports.append(reporter(
                ERROR, self, f'Include \'{self.name}\' should not contain a \'main\'.'
            ))
        
        if not from_doch:
            directives_counter = { root_type: 0 for root_type in [ASTDirectiveConst  , ASTDirectiveConstFromInclude ,
                                                                ASTDirectiveStruct , ASTDirectiveStructFromInclude,
                                                                ASTDirectiveInclude, ASTDirectiveRequireContext,
                                                                ASTDirectiveExtends, ASTDirectiveSetting,
                                                                ASTDirectiveCommand] }
            for directive in self.prog.directives:
                directives_counter[type(directive)] += 1
            directives_counter[ASTDirectiveConst]  += directives_counter[ASTDirectiveConstFromInclude]
            directives_counter[ASTDirectiveStruct] += directives_counter[ASTDirectiveStructFromInclude]
            
            if directives_counter[ASTDirectiveExtends] >= 1 or directives_counter[ASTDirectiveRequireContext] >=1 or \
            directives_counter[ASTDirectiveSetting] >= 1 or directives_counter[ASTDirectiveCommand] >= 1:
                self.reports.append(reporter(
                    ERROR, self, f'Include \'{self.name}\' should not have any diractives besides \'#Include\', \'#Const\' and \'#Struct\'.'
                ))
        
        if not from_doch:
            self.reports.extend(self.prog.reports)

class ASTDirectiveRequireContext (ASTNode):
    
    def __init__(self, p, _class):
        super().__init__([_class], p)
        self._class = _class

class ASTDirectiveExtends (ASTNode):
    
    def __init__ (self, p, filepath, prog):
        super().__init__([filepath], p)
        self.filepath = filepath.content
        self.prog = prog
        self.reports.extend(self.prog.reports)

class ASTDirectiveSetting (ASTNode):
    
    def __init__ (self, p, name, value, showed_name):
        super().__init__([name, value, showed_name], p)
        self.name = name.content
        self.showed_name = None if isinstance(showed_name, ASTTerminalEmpty) else showed_name.value.value
        self.value = MSValue(self.name, value.type, True, value.value.value)

class ASTDirectiveCommand (ASTNode):
    
    def __init__ (self, p, name, type, showed_name):
        super().__init__([name, type, showed_name], p)
        self.name = name.content
        self.showed_name = None if isinstance(showed_name, ASTTerminalEmpty) else showed_name.value.value
        self.value = MSValue(self.name, type, True)