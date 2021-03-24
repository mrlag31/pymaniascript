from .tokens import TokenType
from .lexer import Lexer
from sly.yacc import Parser as SlyParser, ParserMeta as PM, SlyLogger
from pymaniascript.scope import Scope
from pymaniascript.ast import *
from pymaniascript.msobjects import *
import os

COMPUTED_FILES = dict()

__wrapper = PM.__prepare__(None, None)['_']
def __ (token_type, *ruleset):
    def wrapper (f):
        def g (self, p):
            return f(self, p)
        
        g.__name__ = token_type.name
        
        parsed_rules = []
        if not token_type.is_empty():
            for rule in ruleset:
                parsed_rule = []
                
                for elem in rule:
                    if elem.is_precedence():
                        parsed_rule.extend(['%prec', elem.name])
                    else:
                        parsed_rule.append(elem.name)
                
                parsed_rules.append(' '.join(parsed_rule))
        else:
            parsed_rules.append('')
        
        new_wrapper = __wrapper(*parsed_rules)
        return new_wrapper(g)
    return wrapper

class Parser (SlyParser):
    
    tokens = Lexer.tokens
    log = SlyLogger(open(os.devnull, 'w'))
#   debugfile = 'parser.out'
    
    precedence = (
        ('left', *[t.name for t in
            [TokenType.LXR_OPERATOR_AND, TokenType.LXR_OPERATOR_OR]]),

        ('left', *[t.name for t in
            [TokenType.LXR_OPERATOR_EQUAL, TokenType.LXR_OPERATOR_NOT_EQUAL]]),
        
        ('nonassoc', *[t.name for t in
            [TokenType.LXR_OPERATOR_LOWER, TokenType.LXR_OPERATOR_GREATER, TokenType.LXR_OPERATOR_LOWER_EQUAL, TokenType.LXR_OPERATOR_GREATER_EQUAL]]),

		('left', *[t.name for t in
            [TokenType.LXR_OPERATOR_ADD, TokenType.LXR_OPERATOR_SUB, TokenType.LXR_OPERATOR_TEXT_JOIN]]),

		('left', *[t.name for t in
            [TokenType.LXR_OPERATOR_TIMES, TokenType.LXR_OPERATOR_DIV, TokenType.LXR_OPERATOR_MOD]]),

        ('right', *[t.name for t in
            [TokenType.PRC_OPERATOR_UMINUS, TokenType.PRC_OPERATOR_UNOT]]),
        
        ('left', *[t.name for t in 
            [TokenType.LXR_DOT]]),
        
        ('left', *[t.name for t in 
            [TokenType.PRC_IF]]),
        
        ('left', *[t.name for t in 
            [TokenType.LXR_KEYWORD_ELSE]])
    )
    
    start = TokenType.PRS_PROG.name
    
    def __init__ (self, folder):
        super().__init__()
        self.lexer = Lexer()
        self.folder = folder
    
    def __empty (self):
        last = self.symstack[-1]
        
        if last.type == '$end':
            return ASTTerminalEmpty.EMPTY
            
        else:
            last = last.value
            if isinstance(last, list):
                last = last[-1]
            
            return ASTTerminalEmpty(last.end)
    
    def parse_file (self, filepath):
        full_filename = self.folder + os.sep + filepath
        self.reporter = reporter(filepath)
        
        prog = COMPUTED_FILES.get(full_filename, None)
        
        if isinstance(prog, ASTTerminalEmpty):
            prog = ASTProgError(f'Circular import found with script \'{full_filename}\'.', self.reporter)
            COMPUTED_FILES[full_filename] = prog
            return prog
        elif isinstance(prog, ASTProg):
            return prog
        
        try:
            with open(full_filename, 'r') as f: data = f.read()
        except FileNotFoundError:
            prog = ASTProgError(f'File \'{full_filename}\' was not found.', self.reporter)
            COMPUTED_FILES[full_filename] = prog
            return prog
        
        COMPUTED_FILES[full_filename] = ASTTerminalEmpty.EMPTY
        prog = self.parse(data)
        COMPUTED_FILES[full_filename] = prog
        return prog
    
    def parse (self, text):
        tokenizer = self.lexer.tokenize(text)
        self.filescope = Scope()
        self.errored_prog = None
        
        self.currentscope = self.filescope.subscope()
        
        prog = super().parse(tokenizer)
        if self.errored_prog != None:
            return self.errored_prog
        else:
            return prog
    
    def error (self, t):
        if t != None and TokenType[t.type].is_parser_ignored():
            self.errok()
            return next(self.tokens, None)
        
        expected = list(self._lrtable.lr_action[self.state].keys())
        if '$end' in expected:
            expected.remove('$end')
            expected.append('EOF')
        
        if t == None:
            error_msg = 'Unexpected EOF.'
            offender = self.__empty()
        elif TokenType[t.type] == TokenType.LXR_UNKNOWN:
            error_msg = t.value.value
            offender = t.value
        else:
            error_msg = f'Unexpected {t.type}.'
            offender = t.value
        
        if len(expected) <= 1:
            error_msg += f' Expected {expected[0]}.'
        elif len(expected) <= 4:
            expected_msg = ', '.join(expected[:-1]) + f' or {expected[-1]}'
            error_msg += f' Expected {expected_msg}.'
        
        self.errored_prog = ASTProgError(error_msg, self.reporter, offender)
        for tok in self.tokens: continue
        
        self.restart()
        return
    
    # ---
    
    @__(TokenType.PRS_EMPTY)
    def empty (self, p):
        return self.__empty()
    
    # ---
    
    @__(TokenType.PRS_EXPRESSION,
            [TokenType.PRS_EXPRESSION_ACC],
            [TokenType.PRS_EXPRESSION_NONACC])
    def expression (self, p):
        return p[0]
    
    @__(TokenType.PRS_EXPRESSION_LIST,
            [TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION_LIST, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION])
    def expression_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[2]]

    @__(TokenType.PRS_EXPRESSION_ARRAY_KEY_ELEM_LIST,
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ARROW, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION_ARRAY_KEY_ELEM_LIST, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_ARROW, TokenType.PRS_EXPRESSION])
    def expression_array_key_elem_list (self, p):
        if len(p) == 3:
            return [ASTKeyElem(p, p[2], p[0])]
        else:
            return p[0] + [ASTKeyElem([ p[2], p[3], p[4] ], p[4], p[2])]
    
    @__(TokenType.PRS_EXPRESSION_STRUCT_ASSIGN_LIST,
            [TokenType.LXR_IDENT, TokenType.LXR_ASSIGN_EQUAL, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION_STRUCT_ASSIGN_LIST, TokenType.LXR_COMMA, TokenType.LXR_IDENT, TokenType.LXR_ASSIGN_EQUAL, TokenType.PRS_EXPRESSION])
    def expression_struct_assign_list (self, p):
        if len(p) == 3:
            return [ASTStructAssign(p, p[0], p[2])]
        else:
            return p[0] + [ASTStructAssign([ p[2], p[3], p[4] ], p[2], p[4])]
    
    # ---
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.LXR_IDENT])
    def expression_acc_ident (self, p):
        vname = p[0].content
        value = self.currentscope.get_element(vname, MSValue)
        if value == None:
            ret = ASTTerminalValue(p[0], MSValue(vname, VOID))
            ret.reports.append(self.reporter(
                ERROR, ret, f'Variable \'{vname}\' does not exist in this scope.'
            ))
            return ret
        else:
            return ASTTerminalValue(p[0], value)
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION_ACC, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_acc_paren (self, p):
        return p[1]
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION_LIST, TokenType.LXR_BRACKET_ROUND_CL],
            [TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_funccall (self, p):
        vname = p[0].content
        fobj = self.currentscope.get_element(vname, MSFunction)
        args = p[2] if isinstance(p[2], list) else []
        if fobj == None:
            func = ASTTerminalValue(p[0], MSFunction(vname, []))
            func.reports.append(self.reporter(
                ERROR, func, f'Function \'{vname}\' does not exist in this scope.'
            ))
        else:
            func = ASTTerminalValue(p[0], fobj)
        
        return ASTFunctionCall(p, func, args, self.reporter)

    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION_LIST, TokenType.LXR_BRACKET_ROUND_CL],
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_namespace_funccall (self, p):
        fname = p[1].content
        namespace = p[0].value
        fobj = namespace.get_element(fname, MSFunction)
        args = p[3] if isinstance(p[3], list) else []
        if fobj == None:
            func = ASTTerminalValue(p[1], MSFunction(fname, []))
            func.reports.append(self.reporter(
                ERROR, func, f'Function \'{fname}\' does not exist in namespace \'{namespace.name}\'.'
            ))
        else:
            func = ASTTerminalValue(p[1], fobj)
        
        naccess = ASTNamespace([p[0], p[1]], p[0], func)
        return ASTFunctionCall(p, naccess, args, self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.PRS_EXPRESSION_ACC, TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_SQUARE_CL])
    def expression_array (self, p):
        return ASTArray(p, p[0], p[2], self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.PRS_EXPRESSION_ACC, TokenType.LXR_DOT, TokenType.LXR_IDENT],
            [TokenType.PRS_EXPRESSION_ACC, TokenType.LXR_DOT, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION_LIST, TokenType.LXR_BRACKET_ROUND_CL],
            [TokenType.PRS_EXPRESSION_ACC, TokenType.LXR_DOT, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_dot (self, p):
        parent = p[0].value
        
        if len(p) == 3:
            cname = p[2].content
            child = parent.get_attribute(cname)
            if child == None:
                child = ASTTerminalValue(p[2], MSValue(cname, VOID))
                child.reports.append(self.reporter(
                    ERROR, child, f'\'{parent.name}\' has no attribute \'{cname}\'.'
                ))
            else:
                child = ASTTerminalValue(p[2], child)
                
            return ASTDot(p, p[0], child)
        
        else:
            cname = p[2].content
            child = parent.get_method(cname)
            if child == None:
                child = ASTTerminalValue(p[2], MSFunction(cname, []))
                child.reports.append(self.reporter(
                    ERROR, child, f'\'{parent.name}\' has no method \'{cname}\'.'
                ))
            else:
                child = ASTTerminalValue(p[2], child)
                
            dot = ASTDot([p[0], p[1]], p[0], child)
            args = p[4] if isinstance(p[4], list) else []
            
            return ASTFunctionCall(p, dot, args, self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.PRS_EXPRESSION, TokenType.LXR_KEYWORD_AS, TokenType.LXR_TYPE_CLASS],
            [TokenType.LXR_CAST, TokenType.LXR_BRACKET_ROUND_OP, TokenType.LXR_TYPE_CLASS, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_cast (self, p):
        if len(p) == 3:
            cls = p[2].value
            value = MSValue(f'@{cls.name}', cls, True)
            args = [ASTTerminalValue(p[2], value), p[0]]
            func_limits = ASTTerminalEmpty.Empty(p[0].start)
            func = ASTTerminalValue(func_limits, CAST)
        else:
            cls = p[2].value
            value = MSValue(f'@{cls.name}', cls, True)
            args = [ASTTerminalValue(p[2], value), p[4]]
            func = p[0]
        
        return ASTFunctionCall(p, func, args, self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_ACC,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EXPRESSION_STRUCT_ASSIGN_LIST, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_LOCAL_STRUCT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EXPRESSION_STRUCT_ASSIGN_LIST, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_LOCAL_STRUCT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_CURLY_CL],)
    def expression_struct_call (self, p):
        if len(p) == 5:
            sname = p[1].content
            namespace = p[0].value
            struct = namespace.get_element(sname, MSStruct)
            if struct == None:
                struct = ASTTerminalValue(p[1], MSStruct(sname, {}))
                struct.reports.append(self.reporter(
                    ERROR, struct, f'Struct \'{sname}\' does not exist in namespace \'{namespace.name}\'.'
                )) 
            else:
                struct = ASTTerminalValue(p[1], struct)
            
            struct = ASTNamespace(p, p[0], struct)
        
        else:
            struct = p[0]
        
        assigns = p[-2] if isinstance(p[-2], list) else []
        
        return ASTStructCall(p, struct, assigns, self.reporter)
    
    # ---
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_NATURAL],
            [TokenType.LXR_FLOAT],
            [TokenType.LXR_STRING],
            [TokenType.LXR_BOOLEAN],
            [TokenType.LXR_NULL],
            [TokenType.LXR_NULLID])
    def expression_nonacc_direct (self, p):
        return p[0]
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION_NONACC, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_nonacc_paren (self, p):
        return p[1]
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT])
    def expression_namespace_access (self, p):
        vname = p[1].content
        namespace = p[0].value
        obj = namespace.get_element(vname, MSValue)
        if obj == None:
            obj = ASTTerminalValue(p[1], MSValue(vname, VOID))
            obj.reports.append(self.reporter(
                ERROR, obj, f'Attribute \'{vname}\' does not exist in namespace \'{namespace.name}\'.'
            ))
        else:
            obj = ASTTerminalValue(p[1], obj)
        
        return ASTNamespace(p, p[0], obj)
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_ADD, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_SUB, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_TIMES, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_DIV, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_MOD, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_TEXT_JOIN, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_EQUAL, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_NOT_EQUAL, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_GREATER, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_GREATER_EQUAL, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_LOWER, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_LOWER_EQUAL, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_AND, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_OR, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_KEYWORD_IS, TokenType.LXR_TYPE_CLASS])
    def expression_binop (self, p):
        return ASTExpressionBinaryOperation(p, p[0], p[1], p[2], self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_OPERATOR_SUB, TokenType.PRS_EXPRESSION, TokenType.PRC_OPERATOR_UMINUS],
            [TokenType.LXR_OPERATOR_NOT, TokenType.PRS_EXPRESSION, TokenType.PRC_OPERATOR_UNOT])
    def expression_uniop (self, p):
        return ASTExpressionUnaryOperation(p, p[0], p[1], self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_OPERATOR_LOWER, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_GREATER],
            [TokenType.LXR_OPERATOR_LOWER, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_OPERATOR_GREATER])
    def expression_vec (self, p):
        if len(p) == 5:
            return ASTVector(p, [p[1], p[3]], self.reporter)
        else:
            return ASTVector(p, [p[1], p[3], p[5]], self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_DOUBLE_COLON, TokenType.LXR_IDENT],
            [TokenType.PRS_CLASS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_DOUBLE_COLON, TokenType.LXR_IDENT])
    def expression_enum (self, p):
        namespace = p[0].value
        ename = p[1].content
        evname = p[3].content
        enum = None
        
        if isinstance(namespace, MSInclude):
            enum = namespace.get_element(ename, MSEnum)
        elif isinstance(namespace, MSClass):
            enum = namespace.get_enum(ename)
        
        if enum == None:
            enum = ASTTerminalValue(p[1], MSEnum(ename, []))
            enum.reports.append(self.reporter(
                ERROR, enum, f'Enum \'{ename}\' does not exists in namespace \'{namespace.name}\'.'
            ))
        else:
            enum = ASTTerminalValue(p[1], enum)
        
        enum = ASTNamespace([p[0], p[1]], p[0], enum)
        
        enum_value = enum.value.get_value(evname)
        if enum_value == None:
            enum_value = ASTTerminalValue(p[3], MSValue(evname, enum, True))
            enum_value.reports.append(self.reporter(
                ERROR, enum_value, f'Enum \'{enum.value.name}\' has no value \'{evname}\'.'
            ))
        else:
            enum_value = ASTTerminalValue(p[3], enum_value)
        return ASTEnum(p, enum, enum_value)
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_DUMP, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL],
            [TokenType.LXR_DUMPTYPE, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_TYPE, TokenType.LXR_BRACKET_ROUND_CL],
            [TokenType.LXR_TRANSLATE, TokenType.LXR_BRACKET_ROUND_OP, TokenType.LXR_STRING, TokenType.LXR_BRACKET_ROUND_CL])
    def expression_nonacc_special (self, p):
        if p[0].content == DUMP:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
        elif p[0].content == DUMPTYPE:
            value = MSValue(f'@{p[2].value.name}', p[2].value, True)
            arg = ASTTerminalValue(p[2], value)
            return ASTFunctionCall(p, p[0], [arg], self.reporter)
        elif p[0].content == TRANSLATE:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_SQUARE_CL],
            [TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_EXPRESSION_LIST, TokenType.LXR_BRACKET_SQUARE_CL],
            [TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_EXPRESSION_ARRAY_KEY_ELEM_LIST, TokenType.LXR_BRACKET_SQUARE_CL])
    def expression_array_def (self, p):
        elements = p[1] if isinstance(p[1], list) else []
        return ASTArrayDef(p, elements, self.reporter)
    
    # ---
    
    @__(TokenType.PRS_EXPRESSION_NONACC,
            [TokenType.LXR_STRING_AND_CONCAT, TokenType.PRS_EXPRESSION, TokenType.PRS_EXPRESSION_INTERP_STRING, TokenType.LXR_CONCAT_AND_STRING],
            [TokenType.LXR_STRING_AND_CONCAT, TokenType.PRS_EXPRESSION, TokenType.PRS_EMPTY, TokenType.LXR_CONCAT_AND_STRING])
    def expression_interpolated_string (self, p):
        mid = p[2] if isinstance(p[2], list) else []
        return ASTInterpolatedString(p, [p[0], p[1], *mid, p[3]])
    
    @__(TokenType.PRS_EXPRESSION_INTERP_STRING,
            [TokenType.LXR_CONCAT_AND_STRING_AND_CONCAT, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EXPRESSION_INTERP_STRING, TokenType.LXR_CONCAT_AND_STRING_AND_CONCAT, TokenType.PRS_EXPRESSION])
    def expression_interp_string_list (self, p):
        if len(p) == 2:
            return [p[0], p[1]]
        else:
            return p[0] + [p[1], p[2]]
    
    # ---
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON])
    def statement_expression (self, p):
        if p[0].type != VOID:
            p[0].reports.append(self.reporter(
                WARNING, p[0], f'\'{p[0].value.name}\' will be discarded.'
            ))

        return p[0]

    @__(TokenType.PRS_STATEMENT_LIST,
            [TokenType.PRS_STATEMENT],
            [TokenType.PRS_STATEMENT_LIST, TokenType.PRS_STATEMENT])
    def statement_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[1]]
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_BLOCK, TokenType.PRS_EMPTY_OLD_SCOPE])
    def block_to_statement (self, p):
        return p[1]
    
    @__(TokenType.PRS_BLOCK,
            [TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_STATEMENT_LIST, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_CURLY_CL])
    def block (self, p):
        statements = p[1] if isinstance(p[1], list) else []
        block = ASTBlock(p, statements)
        return block
    
    @__(TokenType.PRS_EMPTY_NEW_SCOPE)
    def newscope (self, p):
        self.currentscope = self.currentscope.subscope()
        return self.__empty()

    @__(TokenType.PRS_EMPTY_OLD_SCOPE)
    def oldscope (self, p):
        self.currentscope = self.currentscope.topscope()
        return self.__empty()
    
    # ---
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_DECLARE, TokenType.PRS_DECLARE_STORAGE, TokenType.PRS_DECLARE_TYPE, TokenType.LXR_IDENT, TokenType.PRS_DECLARE_AS, TokenType.PRS_DECLARE_FOR, TokenType.PRS_DECLARE_ASSIGN, TokenType.LXR_SEMICOLON])
    def declare (self, p):
        v = ASTDeclare(p, p[1], p[2], p[3], p[4], p[5], p[6][0], p[6][1], self.reporter)
        
        if self.currentscope.get_element(v.name, MSValue, True) != None:
            v.reports.append(self.reporter(
                ERROR, v, f'\'{v.name}\' was already declared in this block.'
            ))
        else:
            self.currentscope.add_element(v.value)
        
        return v
    
    @__(TokenType.PRS_DECLARE_STORAGE,
            [TokenType.LXR_STORAGE_NETREAD],
            [TokenType.LXR_STORAGE_NETWRITE],
            [TokenType.LXR_STORAGE_METADATA],
            [TokenType.LXR_STORAGE_PERSISTENT],
            [TokenType.PRS_EMPTY])
    def declare_storage (self, p):
        return p[0]
    
    @__(TokenType.PRS_DECLARE_TYPE,
            [TokenType.PRS_TYPE],
            [TokenType.PRS_EMPTY])
    def declare_type (self, p):
        return p[0]
    
    @__(TokenType.PRS_DECLARE_AS,
            [TokenType.LXR_KEYWORD_AS, TokenType.LXR_IDENT],
            [TokenType.PRS_EMPTY])
    def declare_as (self, p):
        return p[-1]

    @__(TokenType.PRS_DECLARE_FOR,
            [TokenType.LXR_KEYWORD_FOR, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EMPTY])
    def declare_for (self, p):
        return p[-1]
    
    @__(TokenType.PRS_DECLARE_ASSIGN,
            [TokenType.LXR_ASSIGN_EQUAL, TokenType.PRS_EXPRESSION],
            [TokenType.LXR_ASSIGN_REF, TokenType.PRS_EXPRESSION],
            [TokenType.PRS_EMPTY])
    def declare_assign (self, p):
        if len(p) == 2:
            return [p[0], p[1]]
        else:
            return [p[0], p[0]]
    
    # ---
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_FOR, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_FOR_NEW_VALUE, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE],
            [TokenType.LXR_KEYWORD_FOR, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_FOR_NEW_VALUE, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE])
    def _for (self, p):
        step = ASTTerminalEmpty(p[7].end) if len(p) == 11 else p[9]
        return ASTFor(p, p[3], p[5], p[7], step, p[-2], self.reporter)
        
    
    @__(TokenType.PRS_FOR_NEW_VALUE,
            [TokenType.LXR_IDENT])
    def for_new_value (self, p):
        value = MSValue(p[0].content, INTEGER, True)
        iterator = ASTTerminalValue(p[0], value)
        
        self.currentscope.add_element(value)
        return iterator
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_FOREACH, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_FOREACH_NEW_VALUES, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE])
    def foreach (self, p):
        iterator = p[3][0]
        array = p[3][1]
        
        return ASTForEach(p, iterator, array, p[5])
    
    @__(TokenType.PRS_FOREACH_NEW_VALUES,
            [TokenType.LXR_IDENT, TokenType.LXR_KEYWORD_IN, TokenType.PRS_EXPRESSION],
            [TokenType.LXR_IDENT, TokenType.LXR_ARROW, TokenType.LXR_IDENT, TokenType.LXR_KEYWORD_IN, TokenType.PRS_EXPRESSION])
    def foreach_new_values (self, p):
        array = p[-1]
        
        if len(p) == 3:
            if not isinstance(array.type, MSArray):
                value = MSValue(p[0].content, VOID, True)
                iterator = ASTTerminalValue(p[0], value)
                array.reports.append(self.reporter(
                    ERROR, array, f'\'{array.value.name}\' is not an array.'
                ))
            else:
                value = MSValue(p[0].content, array.type.elemtype, True)
                iterator = ASTTerminalValue(p[0], value)
            
            self.currentscope.add_element(value)
        
        if len(p) == 5:               
            if not isinstance(array.type, MSArray):
                key = MSValue(p[0].content, VOID, True)
                elem = MSValue(p[2].content, VOID, True)
                key = ASTTerminalValue(p[0], key)
                elem = ASTTerminalValue(p[0], elem)
                array.reports.append(self.reporter(
                    ERROR, array, f'\'{array.value.name}\' is not an array.'
                ))
            else:
                key = MSValue(p[0].content, array.type.keytype, True)
                elem = MSValue(p[2].content, array.type.elemtype, True)
                key = ASTTerminalValue(p[0], key)
                elem = ASTTerminalValue(p[0], elem)
            
            iterator = ASTKeyElem([p[0], p[1], p[2]], elem, key)
            self.currentscope.add_element(elem.value)
            self.currentscope.add_element(key.value)
        
        return [iterator, array]
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_IF, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE, TokenType.PRC_IF],
            [TokenType.LXR_KEYWORD_IF, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE, TokenType.LXR_KEYWORD_ELSE, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE])
    def if_else (self, p):
        if len(p) == 7:
            elseblock = ASTTerminalEmpty(p[5].end)
        else:
            elseblock = p[7]
        return ASTIfElse(p, p[2], p[5], elseblock, self.reporter)
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_WHILE, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE])
    def _while (self, p):
        return ASTWhile(p, p[2], p[5], self.reporter)
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_SWITCH, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_CASE_LIST, TokenType.PRS_DEFAULT, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_KEYWORD_SWITCH, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.PRS_DEFAULT, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_KEYWORD_SWITCHTYPE, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_CASETYPE_LIST, TokenType.PRS_DEFAULT, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_KEYWORD_SWITCHTYPE, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.PRS_DEFAULT, TokenType.LXR_BRACKET_CURLY_CL])
    def switch (self, p):
        mode = 0 if p[0].content == 'switch' else 1
        cases = p[5] if isinstance(p[5], list) else []
        return ASTSwitch(p, p[2], cases, p[6], mode, self.reporter)
    
    @__(TokenType.PRS_CASE_LIST,
            [TokenType.PRS_CASE],
            [TokenType.PRS_CASE_LIST, TokenType.PRS_CASE])
    def case_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[1]]
    
    @__(TokenType.PRS_CASETYPE_LIST,
            [TokenType.PRS_CASETYPE],
            [TokenType.PRS_CASETYPE_LIST, TokenType.PRS_CASETYPE])
    def casetype_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[1]]
    
    @__(TokenType.PRS_CASE,
            [TokenType.LXR_KEYWORD_CASE, TokenType.PRS_EXPRESSION_LIST, TokenType.LXR_COLON, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE])
    def case (self, p):
        return ASTCase(p, p[1], p[4])

    @__(TokenType.PRS_CASETYPE,
            [TokenType.LXR_KEYWORD_CASE, TokenType.PRS_CLASS_LIST, TokenType.LXR_COLON, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE])
    def case (self, p):
        return ASTCase(p, p[1], p[4])
    
    @__(TokenType.PRS_DEFAULT,
            [TokenType.LXR_KEYWORD_DEFAULT, TokenType.LXR_COLON, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_STATEMENT, TokenType.PRS_EMPTY_OLD_SCOPE],
            [TokenType.PRS_EMPTY])
    def default (self, p):
        if len(p) == 3:
            return ASTDefault(p, p[3])
        else:
            return p[0]
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_EQUAL, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_REF, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_ADD, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_SUB, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_TIMES, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_DIV, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_MOD, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_EXPRESSION, TokenType.LXR_ASSIGN_TEXT_JOIN, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON])
    def assign (self, p):
        return ASTAssign(p, p[0], p[1], p[2], self.reporter)
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_TRIPLE_PLUS, TokenType.LXR_IDENT, TokenType.LXR_TRIPLE_PLUS],
            [TokenType.LXR_TRIPLE_MINUS, TokenType.LXR_IDENT, TokenType.LXR_TRIPLE_MINUS])
    def label_call (self, p):
        return ASTLabelCall(p, p[1], p[0])
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_KEYWORD_YIELD, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_KEYWORD_CONTINUE, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_KEYWORD_BREAK, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_KEYWORD_RETURN, TokenType.PRS_EXPRESSION, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_KEYWORD_RETURN, TokenType.PRS_EMPTY, TokenType.LXR_SEMICOLON])
    def statement_special (self, p):
        if p[0].content == 'yield':
            return ASTYield(p)
        elif p[0].content == 'continue':
            return ASTContinue(p)
        elif p[0].content == 'break':
            return ASTBreak(p)
        elif p[0].content == 'return':
            value = ASTTerminalValue(p[1], MSValue('@RETURN', VOID)) if isinstance(p[1], ASTTerminalEmpty) else p[1]
            return ASTReturn(p, value)
    
    @__(TokenType.PRS_STATEMENT,
            [TokenType.LXR_LOG, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_WAIT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_SLEEP, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_ASSERT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_ASSERT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_COMMA, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_TUNINGSTART, TokenType.LXR_BRACKET_ROUND_OP, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_TUNINGMARK, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EXPRESSION, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON],
            [TokenType.LXR_TUNINGEND, TokenType.LXR_BRACKET_ROUND_OP, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_SEMICOLON])
    def statement_special_funccall (self, p):
        if p[0].content == LOG:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
        elif p[0].content == WAIT:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
        elif p[0].content == SLEEP:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
        elif p[0].content == ASSERT:
            if len(p) == 5:
                return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
            else:
                return ASTFunctionCall(p, p[0], [p[2], p[4]], self.reporter)
        elif p[0].content == TUNINGSTART:
            return ASTFunctionCall(p, p[0], [], self.reporter)
        elif p[0].content == TUNINGMARK:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
        elif p[0].content == TUNINGEND:
            return ASTFunctionCall(p, p[0], [], self.reporter)
            
    # ---
    
    @__(TokenType.PRS_NAMESPACE,
            [TokenType.LXR_LOCAL_INCLUDE, TokenType.LXR_DOUBLE_COLON])
    def namespace (self, p):
        return p[0]
    
    @__(TokenType.PRS_CLASS_NAMESPACE,
            [TokenType.LXR_TYPE_CLASS, TokenType.LXR_DOUBLE_COLON])
    def class_namespace (self, p):
        return p[0]
    
    # ---
    
    @__(TokenType.PRS_TYPE,
            [TokenType.LXR_TYPE_CLASS],
            [TokenType.LXR_TYPE_VOID],
            [TokenType.LXR_TYPE_INTEGER],
            [TokenType.LXR_TYPE_REAL],
            [TokenType.LXR_TYPE_TEXT],
            [TokenType.LXR_TYPE_BOOLEAN],
            [TokenType.LXR_TYPE_IDENT],
            [TokenType.LXR_TYPE_INT2],
            [TokenType.LXR_TYPE_INT3],
            [TokenType.LXR_TYPE_VEC2],
            [TokenType.LXR_TYPE_VEC3],
            [TokenType.LXR_LOCAL_STRUCT])
    def type_direct (self, p):
        return p[0]
    
    @__(TokenType.PRS_CLASS_LIST,
            [TokenType.LXR_TYPE_CLASS],
            [TokenType.PRS_CLASS_LIST, TokenType.LXR_COMMA, TokenType.LXR_TYPE_CLASS])
    def class_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[2]]
    
    @__(TokenType.PRS_TYPE,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT],
            [TokenType.PRS_CLASS_NAMESPACE, TokenType.LXR_IDENT])
    def type_exterior (self, p):
        namespace = p[0].value
        tname = p[1].content
        type = None
        
        if isinstance(namespace, MSInclude):
            type = namespace.get_element(tname, MSEnum)
            if type == None: namespace.get_element(tname, MSStruct)
        elif isinstance(namespace, MSClass):
            type = namespace.get_enum(tname)
        
        if type == None:
            type = ASTTerminalValue(p[1], VOID)
            type.reports.append(self.reporter(
                ERROR, type, f'Struct or enum \'{tname}\' does not exist in namespace {namespace.name}.'
            ))
        else:
            type = ASTTerminalValue(p[1], type)
        
        return ASTNamespace(p, p[0], type)
    
    @__(TokenType.PRS_TYPE,
            [TokenType.PRS_TYPE, TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_SQUARE_CL],
            [TokenType.PRS_TYPE, TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_TYPE, TokenType.LXR_BRACKET_SQUARE_CL])
    def type_array (self, p):
        elemtype = p[0]
        keytype = None if isinstance(p[2], ASTTerminalEmpty) else p[2]
        
        return ASTTypeArray(p, elemtype, keytype)
    
    # ---
    
    @__(TokenType.PRS_GLOBAL_DEFINITION_LIST,
            [TokenType.PRS_GLOBAL_DEFINITION],
            [TokenType.PRS_GLOBAL_DEFINITION_LIST, TokenType.PRS_GLOBAL_DEFINITION])
    def global_definition_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[1]]
    
    @__(TokenType.PRS_GLOBAL_DEFINITION,
            [TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_FUNCDEF_NEW, TokenType.PRS_BLOCK, TokenType.PRS_EMPTY_OLD_SCOPE])
    def global_function_definition (self, p):
        type, name, args = p[1]
        func = ASTFunctionDefinition(p, type, name, args, p[2], self.reporter)
        
        return func
    
    @__(TokenType.PRS_FUNCDEF_NEW,
            [TokenType.PRS_TYPE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_FUNCDEF_ARGS, TokenType.LXR_BRACKET_ROUND_CL],
            [TokenType.PRS_TYPE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_ROUND_CL])
    def new_function (self, p):
        args = p[3] if isinstance(p[3], list) else []
        sign = ( *[argtype.value for argtype in args[::2]], p[0].value )
        
        fobj = self.filescope.get_element(p[1].content, MSFunction)
        if fobj == None:
            fobj = MSFunction(p[1].content, [sign])
            self.filescope.add_element(fobj)
        else:
            fobj.signatures.append(sign)
        
        return [p[0], p[1], args]
    
    @__(TokenType.PRS_FUNCDEF_ARGS,
            [TokenType.PRS_TYPE, TokenType.LXR_IDENT],
            [TokenType.PRS_FUNCDEF_ARGS, TokenType.LXR_COMMA, TokenType.PRS_TYPE, TokenType.LXR_IDENT])
    def funcdef_args (self, p):
        if len(p) == 2:
            value = MSValue(p[1].content, p[0].value)
            self.currentscope.add_element(value)
            return [p[0], p[1]]
        else:
            value = MSValue(p[3].content, p[2].value)
            self.currentscope.add_element(value)
            return p[0] + [p[2], p[3]]

    @__(TokenType.PRS_GLOBAL_DEFINITION,
            [TokenType.LXR_KEYWORD_DECLARE, TokenType.PRS_DECLARE_STORAGE, TokenType.PRS_DECLARE_TYPE, TokenType.LXR_IDENT, TokenType.PRS_DECLARE_AS, TokenType.PRS_DECLARE_FOR, TokenType.PRS_DECLARE_ASSIGN, TokenType.LXR_SEMICOLON])
    def global_declare (self, p):
        v = ASTDeclare(p, p[1], p[2], p[3], p[4], p[5], p[6][0], p[6][1], self.reporter, True)
        
        if self.currentscope.get_element(v.name, MSValue, True) != None:
            v.reports.append(self.reporter(
                ERROR, v, f'\'{v.name}\' was already declared in this block.'
            ))
        else:
            self.currentscope.add_element(v.value)
        
        return v
    
    @__(TokenType.PRS_GLOBAL_DEFINITION,
            [TokenType.LXR_TRIPLE_ASTERISK, TokenType.LXR_IDENT, TokenType.LXR_TRIPLE_ASTERISK, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.LXR_TRIPLE_ASTERISK, TokenType.PRS_STATEMENT_LIST, TokenType.PRS_EMPTY_OLD_SCOPE, TokenType.LXR_TRIPLE_ASTERISK])
    def label_def (self, p):
        label = ASTLabelDef(p, p[1], ASTBlock(p[5], p[5]))
        self.filescope.add_element(label.value)
        return label
    
    # ---
    
    @__(TokenType.PRS_LITERAL_LIST,
            [TokenType.PRS_LITERAL],
            [TokenType.PRS_LITERAL_LIST, TokenType.LXR_COMMA, TokenType.PRS_LITERAL])
    def literal_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[2]]

    @__(TokenType.PRS_LITERAL_ARRAY_KEY_ELEM_LIST,
            [TokenType.PRS_LITERAL, TokenType.LXR_ARROW, TokenType.PRS_LITERAL],
            [TokenType.PRS_LITERAL_ARRAY_KEY_ELEM_LIST, TokenType.LXR_COMMA, TokenType.PRS_LITERAL, TokenType.LXR_ARROW, TokenType.PRS_LITERAL])
    def literal_array_key_elem_list (self, p):
        if len(p) == 3:
            return [ASTKeyElem(p, p[2], p[0])]
        else:
            return p[0] + [ASTKeyElem([ p[2], p[3], p[4] ], p[4], p[2])]
    
    @__(TokenType.PRS_LITERAL_STRUCT_ASSIGN_LIST,
            [TokenType.LXR_IDENT, TokenType.LXR_ASSIGN_EQUAL, TokenType.PRS_LITERAL],
            [TokenType.PRS_LITERAL_STRUCT_ASSIGN_LIST, TokenType.LXR_COMMA, TokenType.LXR_IDENT, TokenType.LXR_ASSIGN_EQUAL, TokenType.PRS_LITERAL])
    def literal_struct_assign_list (self, p):
        if len(p) == 3:
            return [ASTStructAssign(p, p[0], p[2])]
        else:
            return p[0] + [ASTStructAssign([ p[2], p[3], p[4] ], p[2], p[4])]
    
    @__(TokenType.PRS_LITERAL,
            [TokenType.LXR_NATURAL],
            [TokenType.LXR_FLOAT],
            [TokenType.LXR_STRING],
            [TokenType.LXR_BOOLEAN],
            [TokenType.LXR_NULL],
            [TokenType.LXR_NULLID])
    def literal_direct (self, p):
        return p[0]

    @__(TokenType.PRS_LITERAL,
            [TokenType.LXR_OPERATOR_SUB, TokenType.PRS_LITERAL, TokenType.PRC_OPERATOR_UMINUS])
    def literal_uniop (self, p):
        return ASTExpressionUnaryOperation(p, p[0], p[1], self.reporter)
    
    @__(TokenType.PRS_LITERAL,
            [TokenType.LXR_OPERATOR_LOWER, TokenType.PRS_LITERAL, TokenType.LXR_COMMA, TokenType.PRS_LITERAL, TokenType.LXR_OPERATOR_GREATER],
            [TokenType.LXR_OPERATOR_LOWER, TokenType.PRS_LITERAL, TokenType.LXR_COMMA, TokenType.PRS_LITERAL, TokenType.LXR_COMMA, TokenType.PRS_LITERAL, TokenType.LXR_OPERATOR_GREATER])
    def literal_vec (self, p):
        if len(p) == 5:
            return ASTVector(p, [p[1], p[3]], self.reporter)
        else:
            return ASTVector(p, [p[1], p[3], p[5]], self.reporter)
    
    @__(TokenType.PRS_LITERAL,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_DOUBLE_COLON, TokenType.LXR_IDENT],
            [TokenType.PRS_CLASS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_DOUBLE_COLON, TokenType.LXR_IDENT])
    def literal_enum (self, p):
        namespace = p[0].value
        ename = p[1].content
        evname = p[3].content
        enum = None
        
        if isinstance(namespace, MSInclude):
            enum = namespace.get_element(ename, MSEnum)
        elif isinstance(namespace, MSClass):
            enum = namespace.get_enum(ename)
        
        if enum == None:
            enum = ASTTerminalValue(p[1], MSEnum(ename, []))
            enum.reports.append(self.reporter(
                ERROR, enum, f'Enum \'{ename}\' does not exist in namespace {namespace.name}.'
            ))
        else:
            enum = ASTTerminalValue(p[1], enum)
        
        enum = ASTNamespace([p[0], p[1]], p[0], enum)
        
        enum_value = enum.value.get_value(evname)
        if enum_value == None:
            enum_value = ASTTerminalValue(p[3], MSValue(evname, enum, True))
            enum_value.reports.append(self.reporter(
                ERROR, enum_value, f'Enum \'{enum.value.name}\' has no value \'{evname}\'.'
            ))
        else:
            enum_value = ASTTerminalValue(p[3], enum_value)
        return ASTEnum(p, enum, enum_value)

    @__(TokenType.PRS_LITERAL,
            [TokenType.LXR_TRANSLATE, TokenType.LXR_BRACKET_ROUND_OP, TokenType.LXR_STRING, TokenType.LXR_BRACKET_ROUND_CL])
    def literal_special (self, p):
        if p[0].content == TRANSLATE:
            return ASTFunctionCall(p, p[0], [p[2]], self.reporter)
    
    @__(TokenType.PRS_LITERAL,
            [TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_SQUARE_CL],
            [TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_LITERAL_LIST, TokenType.LXR_BRACKET_SQUARE_CL],
            [TokenType.LXR_BRACKET_SQUARE_OP, TokenType.PRS_LITERAL_ARRAY_KEY_ELEM_LIST, TokenType.LXR_BRACKET_SQUARE_CL])
    def literal_array_def (self, p):
        elements = p[1] if isinstance(p[1], list) else []
        return ASTArrayDef(p, elements, self.reporter)
    
    @__(TokenType.PRS_LITERAL,
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_LITERAL_STRUCT_ASSIGN_LIST, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_LOCAL_STRUCT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_LITERAL_STRUCT_ASSIGN_LIST, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_LOCAL_STRUCT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_CURLY_CL],)
    def literal_struct_call (self, p):
        if len(p) == 5:
            sname = p[1].content
            namespace = p[0].value
            struct = namespace.get_element(sname, MSStruct)
            if struct == None:
                struct = ASTTerminalValue(p[1], MSStruct(sname, {}))
                struct.reports.append(self.reporter(
                    ERROR, struct, f'Struct \'{sname}\' does not exist in namespace \'{namespace.name}\'.'
                )) 
            else:
                struct = ASTTerminalValue(p[1], struct)
            
            struct = ASTNamespace(p, p[0], struct)
        
        else:
            struct = p[0]
        
        assigns = p[-2] if isinstance(p[-2], list) else []
        
        return ASTStructCall(p, struct, assigns, self.reporter)
    
    # ---
    
    @__(TokenType.PRS_DIRECTIVE_LIST,
            [TokenType.PRS_DIRECTIVE],
            [TokenType.PRS_DIRECTIVE_LIST, TokenType.PRS_DIRECTIVE])
    def directive_list (self, p):
        if len(p) == 1:
            return [p[0]]
        else:
            return p[0] + [p[1]]
    
    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_CONST, TokenType.LXR_IDENT, TokenType.PRS_LITERAL],
            [TokenType.LXR_DIRECTIVE_CONST, TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_KEYWORD_AS, TokenType.LXR_IDENT])
    def directive_const (self, p):
        if len(p) == 3:
            const = ASTDirectiveConst(p, p[1], p[2])
        else:
            vname = p[2].content
            namespace = p[1].value
            obj = namespace.get_element(vname, MSValue)
            if obj == None:
                obj = ASTTerminalValue(p[2], MSValue(vname, VOID))
                obj.reports.append(self.reporter(
                    ERROR, obj, f'Value \'{vname}\' does not exist in namespace \'{namespace.name}\'.'
                )) 
            else:
                obj = ASTTerminalValue(p[2], obj)
            
            namespace = ASTNamespace([p[1], p[2]], p[1], obj)
            const = ASTDirectiveConstFromInclude(p, namespace, p[4])
        
        if self.filescope.get_element(const.value.name, MSValue) != None:
            const.reports.append(self.reporter(
                ERROR, const, f'Const \'{const.value.name}\' already exists.'
            )) 
        else:
            self.filescope.add_element(const.value)
        
        if not const.value.name.startswith('C_'):
            const.reports.append(self.reporter(
                WARNING, const, f'Const name \'{const.value.name}\' should start with \'C_\'.'
            )) 
            
        return const
    
    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_STRUCT, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_DIRECTIVE_STRUCT_ARGS, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_DIRECTIVE_STRUCT, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_CURLY_OP, TokenType.PRS_EMPTY, TokenType.LXR_BRACKET_CURLY_CL],
            [TokenType.LXR_DIRECTIVE_STRUCT, TokenType.PRS_NAMESPACE, TokenType.LXR_IDENT, TokenType.LXR_KEYWORD_AS, TokenType.LXR_IDENT])
    def directive_struct (self, p):
        if isinstance(p[1], ASTTerminal):
            struct_args = p[3] if isinstance(p[3], list) else []
            struct = ASTDirectiveStruct(p, p[1], struct_args)
        else:
            sname = p[1].content
            namespace = p[0].value
            sobj = namespace.get_element(sname, MSStruct)
            if sobj == None:
                sobj = ASTTerminalValue(p[1], MSStruct(sname, {}))
                sobj.reports.append(self.reporter(
                    ERROR, sobj, f'Struct \'{sname}\' does not exist in namespace \'{namespace.name}\'.'
                )) 
            else:
                sobj = ASTTerminalValue(p[1], sobj)
            
            namespace = ASTNamespace(p, p[0], sobj)
            struct = ASTDirectiveStructFromInclude(p, namespace, p[4])
        
        if self.filescope.get_element(struct.struct.name, MSValue) != None:
            struct.reports.append(self.reporter(
                ERROR, struct, f'Struct \'{struct.struct.name}\' already exists.'
            )) 
        else:
            self.filescope.add_element(struct.struct)
            self.lexer.local_structs[struct.struct.name] = struct.struct
        return struct
    
    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_INCLUDE, TokenType.PRS_LITERAL, TokenType.LXR_KEYWORD_AS, TokenType.LXR_IDENT])
    def directive_include (self, p):
        filepath = p[1]
        if filepath.type != TEXT:
            filepath.reports.append(self.reporter(
                ERROR, filepath, 'File path type must be text.'
            ))
            filepath = ''
        else:
            filepath = filepath.value.value
        
        if filepath in NAMESPACES:
            include = ASTDirectiveInclude(p, p[1], p[3], NAMESPACES[filepath], self.reporter, True)
        else:
            prs = Parser(self.folder)
            prog = prs.parse_file(filepath)
            if isinstance(prog, ASTProgError):
                prog.reports.append(self.reporter(
                    ERROR, prog, f'\'{filepath}\' was not found or did not compile.'
                ))
            include = ASTDirectiveInclude(p, p[1], p[3], prog, self.reporter)
            
        self.lexer.local_includes[include.name] = include.include
        return include
    
    @__(TokenType.PRS_DIRECTIVE_STRUCT_ARGS,
            [TokenType.PRS_TYPE, TokenType.LXR_IDENT, TokenType.LXR_SEMICOLON],
            [TokenType.PRS_DIRECTIVE_STRUCT_ARGS, TokenType.PRS_TYPE, TokenType.LXR_IDENT, TokenType.LXR_SEMICOLON])
    def directive_struct_args (self, p):
        if len(p) == 3:
            return [p[0], p[1]]
        else:
            return p[0] + [p[1], p[2]]
    
    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_REQUIRECONTEXT, TokenType.LXR_TYPE_CLASS])
    def directive_require_context (self, p):
        type = p[1].value
        reqctx = ASTDirectiveRequireContext(p, p[1])
        
        if self.currentscope.get_element('This', MSValue) != None:
            reqctx.reports.append(self.reporter(
                ERROR, reqctx, '\'This\' has already been defined in this scope (either by a constant or by another #RequireContext).'
            ))
        else:
            self.currentscope.add_element(MSValue('This', p[1].value, True))
            self.filescope.add_element(MSValue('@THIS', p[1].value, True))
        
            while type != None:
                for attribute in type.attributes.values():
                    self.currentscope.add_element(attribute)
                for method in type.methods.values():
                    self.currentscope.add_element(method)
                type = type.parent
            
        return reqctx
    
    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_EXTENDS, TokenType.PRS_LITERAL])
    def directive_extends (self, p):
        filepath = p[1]
        if filepath.type != TEXT:
            filepath.reports.append(self.reporter(
                ERROR, filepath, 'File path type must be text.'
            ))
            filepath = ''
        else:
            filepath = filepath.value.value
            
        prs = Parser(self.folder)
        prog = prs.parse_file(filepath)
        if isinstance(prog, ASTProgError):
            prog.reports.append(self.reporter(
                ERROR, prog, f'\'{filepath}\' was not found or did not compile.'
            ))
        
        for type, objects in prog.scope.elements.items():
            for obj in objects.values():
                if self.filescope.get_element(obj.name, type) != None:
                    prog.reports.append(self.reporter(
                        ERROR, prog, f'Object \'{obj.name}\' already exists.'
                    ))
                else:
                    self.filescope.add_element(obj)
                    if obj.name == '@THIS':
                        self.currentscope.add_element(MSValue('This', obj.type, True))
                    
        extends = ASTDirectiveExtends(p, p[1], prog)
        
        return extends
    
    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_SETTING, TokenType.LXR_IDENT, TokenType.PRS_LITERAL, TokenType.LXR_KEYWORD_AS, TokenType.PRS_LITERAL],
            [TokenType.LXR_DIRECTIVE_SETTING, TokenType.LXR_IDENT, TokenType.PRS_LITERAL])
    def directive_setting (self, p):
        if len(p) == 3:
            empty = ASTTerminalEmpty(p[2].end)
            setting = ASTDirectiveSetting(p, p[1], p[2], empty)
        else:
            setting = ASTDirectiveSetting(p, p[1], p[2], p[4])
        
        if self.filescope.get_element(setting.value.name, MSValue) != None:
            setting.reports.append(self.reporter(
                ERROR, setting, f'Setting \'{setting.value.name}\' already exists.'
            )) 
        else:
            self.filescope.add_element(setting.value)
        
        if not setting.value.name.startswith('S_'):
            setting.reports.append(self.reporter(
                WARNING, setting, f'Setting name \'{setting.value.name}\' should start with \'S_\'.'
            )) 
        
        return setting

    @__(TokenType.PRS_DIRECTIVE,
            [TokenType.LXR_DIRECTIVE_COMMAND, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_TYPE, TokenType.LXR_BRACKET_ROUND_CL, TokenType.LXR_KEYWORD_AS, TokenType.PRS_LITERAL],
            [TokenType.LXR_DIRECTIVE_COMMAND, TokenType.LXR_IDENT, TokenType.LXR_BRACKET_ROUND_OP, TokenType.PRS_TYPE, TokenType.LXR_BRACKET_ROUND_CL])
    def directive_setting (self, p):
        if len(p) == 5:
            empty = ASTTerminalEmpty(p[4].end)
            setting = ASTDirectiveCommand(p, p[1], p[3], empty)
        else:
            setting = ASTDirectiveCommand(p, p[1], p[3], p[6])
        
        self.currentscope.add_element(setting.value)
        return setting
    
    # ---
    
    @__(TokenType.PRS_MAIN,
            [TokenType.LXR_KEYWORD_MAIN, TokenType.LXR_BRACKET_ROUND_OP, TokenType.LXR_BRACKET_ROUND_CL, TokenType.PRS_EMPTY_NEW_SCOPE, TokenType.PRS_BLOCK, TokenType.PRS_EMPTY_OLD_SCOPE])
    def main (self, p):
        main_limits = ASTTerminalEmpty.Empty(p[0].start)
        main_type = ASTTerminalValue(main_limits, VOID)
        return ASTMain(p, main_type, p[0], p[4])
    
    @__(TokenType.PRS_PROG,
            [TokenType.PRS_DIRECTIVE_LIST, TokenType.PRS_GLOBAL_DEFINITION_LIST, TokenType.PRS_MAIN],
            [TokenType.PRS_DIRECTIVE_LIST, TokenType.PRS_GLOBAL_DEFINITION_LIST, TokenType.PRS_EMPTY],
            [TokenType.PRS_DIRECTIVE_LIST, TokenType.PRS_EMPTY, TokenType.PRS_MAIN],
            [TokenType.PRS_DIRECTIVE_LIST, TokenType.PRS_EMPTY, TokenType.PRS_EMPTY],
            [TokenType.PRS_EMPTY, TokenType.PRS_GLOBAL_DEFINITION_LIST, TokenType.PRS_MAIN],
            [TokenType.PRS_EMPTY, TokenType.PRS_GLOBAL_DEFINITION_LIST, TokenType.PRS_EMPTY],
            [TokenType.PRS_EMPTY, TokenType.PRS_EMPTY, TokenType.PRS_MAIN],
            [TokenType.PRS_EMPTY, TokenType.PRS_EMPTY, TokenType.PRS_EMPTY])
    def prog (self, p):
        declares = p[0] if isinstance(p[0], list) else []
        definitions = p[1] if isinstance(p[1], list) else []
        return ASTProg(p, declares, definitions, p[2], self.filescope, self.reporter)