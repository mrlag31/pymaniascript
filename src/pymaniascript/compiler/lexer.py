from sly.lex import Lexer as SlyLexer, LexerMeta as LM
from .tokens import TokenType
from pymaniascript.ast import Index, ASTTerminalValue, ASTTerminal
from pymaniascript.msobjects import *

__wrapper = LM.__prepare__(None, None)['_']
def __ (token_type, *regexes):
    def wrapper (f):
        def g (self, t):
            t.type = token_type.name
            return f(self, t)
        
        g.__name__ = token_type.name
        if len(regexes) != 0:
            new_wrapper = __wrapper(*regexes)
            return new_wrapper(g)
        else:
            return g
        
    return wrapper

KEYWORDS_CONTROL = {
    'main': TokenType.LXR_KEYWORD_MAIN,
    'if': TokenType.LXR_KEYWORD_IF,
    'else': TokenType.LXR_KEYWORD_ELSE,
    'while': TokenType.LXR_KEYWORD_WHILE,
    'for': TokenType.LXR_KEYWORD_FOR,
    'foreach': TokenType.LXR_KEYWORD_FOREACH,
    'switch': TokenType.LXR_KEYWORD_SWITCH,
    'switchtype': TokenType.LXR_KEYWORD_SWITCHTYPE,
    'case': TokenType.LXR_KEYWORD_CASE,
    'default': TokenType.LXR_KEYWORD_DEFAULT,
    'yield': TokenType.LXR_KEYWORD_YIELD,
    'continue': TokenType.LXR_KEYWORD_CONTINUE,
    'break': TokenType.LXR_KEYWORD_BREAK,
    'return': TokenType.LXR_KEYWORD_RETURN,
    'is': TokenType.LXR_KEYWORD_IS,
    'as': TokenType.LXR_KEYWORD_AS,
    'in': TokenType.LXR_KEYWORD_IN,
    'declare': TokenType.LXR_KEYWORD_DECLARE,
    
    'netread': TokenType.LXR_STORAGE_NETREAD,
    'netwrite': TokenType.LXR_STORAGE_NETWRITE,
    'persistent': TokenType.LXR_STORAGE_PERSISTENT,
    'metadata': TokenType.LXR_STORAGE_METADATA,
}

KEYWORDS_ELEMS = {
    elem[0].name: elem for elem in [
        (CAST, TokenType.LXR_CAST),
        (LOG, TokenType.LXR_LOG),
        (WAIT, TokenType.LXR_WAIT),
        (SLEEP, TokenType.LXR_SLEEP),
        (ASSERT, TokenType.LXR_ASSERT),
        (TUNINGSTART, TokenType.LXR_TUNINGSTART),
        (TUNINGMARK, TokenType.LXR_TUNINGMARK),
        (TUNINGEND, TokenType.LXR_TUNINGEND),
        (TRANSLATE, TokenType.LXR_TRANSLATE),
        (DUMP, TokenType.LXR_DUMP),
        (DUMPTYPE, TokenType.LXR_DUMPTYPE),

        (TRUE, TokenType.LXR_BOOLEAN),
        (FALSE, TokenType.LXR_BOOLEAN),
        (NULL, TokenType.LXR_NULL),
        (NULLID, TokenType.LXR_NULLID),

        *[ (c, TokenType.LXR_TYPE_CLASS) for c in CLASSES.values() ],

        (VOID, TokenType.LXR_TYPE_VOID),
        (INTEGER, TokenType.LXR_TYPE_INTEGER),
        (REAL, TokenType.LXR_TYPE_REAL),
        (TEXT, TokenType.LXR_TYPE_TEXT),
        (BOOLEAN, TokenType.LXR_TYPE_BOOLEAN),
        (IDENT, TokenType.LXR_TYPE_IDENT),
        (INT2, TokenType.LXR_TYPE_INT2),
        (INT3, TokenType.LXR_TYPE_INT3),
        (VEC2, TokenType.LXR_TYPE_VEC2),
        (VEC3, TokenType.LXR_TYPE_VEC3),
    ]
}

class Limit:
    
    def __init__(self, start, end):
        self.start, self.end = start, end

class Lexer (SlyLexer):

    tokens = [t.name for t in TokenType if t.is_lexer() and not t.is_lexer_ignored()]
    
    def __get_index (self, index):
        return Index(index, self.text)
    
    def __get_limit (self, t):
        return Limit(self.__get_index(t.index), self.__get_index(self.index))
    
    def tokenize (self, text):
        self.local_structs, self.local_includes, self.token_stack = dict(), dict(), list()
        tokenizer = super().tokenize(text)
        
        def _tokenizer ():           
            for tok in tokenizer:
                self.token_stack.append(tok.value)
                yield tok
        return _tokenizer()
    
    @__(TokenType.LXR_UNKNOWN)
    def error (self, t):
        limit = Limit(self.__get_index(self.index), self.__get_index(self.index+1))
        t.value = ASTTerminalValue(limit, f'Unexpected character \'{t.value[0]}\'.')
        self.index += 1
        return t

    # ---

    def __basic (self, t):
        t.value = ASTTerminal(self.__get_limit(t), t.value)
        return t
    
    def __triple (self, t):
        t.value = t.value[3:-3]
        return self.__basic(t)

    # ---

    @__(TokenType.LXR_WHITESPACE, r'\s+')
    def whitespace (self, t): pass
    
    comments = __(TokenType.LXR_COMMENT, r'(//.*)|(/\*(.|\n)*?\*/)')(__basic)

    # ---

    @__(TokenType.LXR_FLOAT, r'[0-9]+[eE][+-]?[0-9]+', r'[0-9]+\.(?![0-9])([eE][+-]?[0-9]+)?', r'[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?')
    def decimal (self, t):
        t.value = ASTTerminalValue(self.__get_limit(t), MSValue('@LITERAL', REAL, True, float(t.value)))
        return t

    @__(TokenType.LXR_NATURAL, r'[0-9]+(?![0-9]*\.)')
    def integer (self, t):
        t.value = ASTTerminalValue(self.__get_limit(t), MSValue('@LITERAL', INTEGER, True, int(t.value)))
        return t
    
    @__(TokenType.LXR_IDENT, r'[a-zA-Z_][a-zA-Z0-9_]*')
    def ident (self, t):
        if   t.value in KEYWORDS_CONTROL:
            t.type = KEYWORDS_CONTROL[t.value].name
            t.value = ASTTerminal(self.__get_limit(t), t.value)
        elif t.value in KEYWORDS_ELEMS:
            elem = KEYWORDS_ELEMS[t.value]
            t.type = elem[1].name
            t.value = ASTTerminalValue(self.__get_limit(t), elem[0])
        elif t.value in self.local_structs:
            t.type = TokenType.LXR_LOCAL_STRUCT.name 
            t.value = ASTTerminalValue(self.__get_limit(t), self.local_structs[t.value])
        elif t.value in self.local_includes:
            t.type = TokenType.LXR_LOCAL_INCLUDE.name 
            t.value = ASTTerminalValue(self.__get_limit(t), self.local_includes[t.value])
        else:
            t.type = TokenType.LXR_IDENT.name
            t.value = ASTTerminal(self.__get_limit(t), t.value)
        
        return t

    # ---

    @__(TokenType.LXR_STRING, r'\"(?!\"\")([^\\\n]|(\\.)|(\\\n))*?\"', r'\"\"\"([^{]|{(?!{{))*?\"\"\"')
    def string (self, t):           
        if   t.value.startswith('\"\"\"'):
            t.value = t.value[3:-3]
        elif t.value.startswith('\"'):
            t.value = t.value[1:-1]

        t.value = ASTTerminalValue(self.__get_limit(t), MSValue('@LITERAL', TEXT, True, t.value))
        return t

    string_and_concat            = __(TokenType.LXR_STRING_AND_CONCAT           , r'\"\"\"([^\"]|\"(?!\"\"))*?{{{')(__triple)
    concat_and_string            = __(TokenType.LXR_CONCAT_AND_STRING           , r'}}}([^{]|{(?!{{))*?\"\"\"'    )(__triple)
    concat_and_string_and_concat = __(TokenType.LXR_CONCAT_AND_STRING_AND_CONCAT, r'}}}([^\"]|\"(?!\"\"))*?{{{'   )(__triple)

    # ---

    bracket_round_op  = __(TokenType.LXR_BRACKET_ROUND_OP , r'\(')(__basic)
    bracket_round_cl  = __(TokenType.LXR_BRACKET_ROUND_CL , r'\)')(__basic)
    brakcet_curly_op  = __(TokenType.LXR_BRACKET_CURLY_OP , r'{' )(__basic)
    bracket_curly_cl  = __(TokenType.LXR_BRACKET_CURLY_CL , r'}' )(__basic)
    bracket_square_op = __(TokenType.LXR_BRACKET_SQUARE_OP, r'\[')(__basic)
    bracket_square_cl = __(TokenType.LXR_BRACKET_SQUARE_CL, r'\]')(__basic)

    # ---

    require_context = __(TokenType.LXR_DIRECTIVE_REQUIRECONTEXT, r'#RequireContext')(__basic)
    extends         = __(TokenType.LXR_DIRECTIVE_EXTENDS       , r'#Extends'       )(__basic)
    include         = __(TokenType.LXR_DIRECTIVE_INCLUDE       , r'#Include'       )(__basic)
    setting         = __(TokenType.LXR_DIRECTIVE_SETTING       , r'#Setting'       )(__basic)
    command         = __(TokenType.LXR_DIRECTIVE_COMMAND       , r'#Command'       )(__basic)
    const           = __(TokenType.LXR_DIRECTIVE_CONST         , r'#Const'         )(__basic)
    struct          = __(TokenType.LXR_DIRECTIVE_STRUCT        , r'#Struct'        )(__basic)

    # ---

    comma           = __(TokenType.LXR_COMMA          , r','     )(__basic)
    semicolon       = __(TokenType.LXR_SEMICOLON      , r';'     )(__basic)
    colon           = __(TokenType.LXR_COLON          , r':(?!:)')(__basic)
    double_colon    = __(TokenType.LXR_DOUBLE_COLON   , r'::'    )(__basic)
    dot             = __(TokenType.LXR_DOT            , r'\.'    )(__basic)
    arrow           = __(TokenType.LXR_ARROW          , r'=>'    )(__basic)
    triple_plus     = __(TokenType.LXR_TRIPLE_PLUS    , r'\+\+\+')(__basic)
    triple_minus    = __(TokenType.LXR_TRIPLE_MINUS   , r'---'   )(__basic)
    triple_asterisk = __(TokenType.LXR_TRIPLE_ASTERISK, r'\*\*\*')(__basic)

    # ---

    operator_add           = __(TokenType.LXR_OPERATOR_ADD          , r'\+(?!(\+\+|=))')(__basic)
    operator_sub           = __(TokenType.LXR_OPERATOR_SUB          , r'-(?!(--|=))'   )(__basic)
    operator_times         = __(TokenType.LXR_OPERATOR_TIMES        , r'\*(?!(\*\*|=))')(__basic)
    operator_div           = __(TokenType.LXR_OPERATOR_DIV          , r'/(?!=)'        )(__basic)
    operator_mod           = __(TokenType.LXR_OPERATOR_MOD          , r'%(?!=)'        )(__basic)
    operator_text_join     = __(TokenType.LXR_OPERATOR_TEXT_JOIN    , r'\^(?!=)'       )(__basic)
    operator_equal         = __(TokenType.LXR_OPERATOR_EQUAL        , r'=='            )(__basic)
    operator_not_equal     = __(TokenType.LXR_OPERATOR_NOT_EQUAL    , r'!='            )(__basic)
    operator_not           = __(TokenType.LXR_OPERATOR_NOT          , r'!(?!=)'        )(__basic)
    operator_greater       = __(TokenType.LXR_OPERATOR_GREATER      , r'>(?!=)'        )(__basic)
    operator_greater_equal = __(TokenType.LXR_OPERATOR_GREATER_EQUAL, r'>='            )(__basic)
    operator_lower         = __(TokenType.LXR_OPERATOR_LOWER        , r'<(?!=)'        )(__basic)
    operator_lower_equal   = __(TokenType.LXR_OPERATOR_LOWER_EQUAL  , r'<=(?!>)'       )(__basic)
    operator_and           = __(TokenType.LXR_OPERATOR_AND          , r'&&'            )(__basic)
    operator_or            = __(TokenType.LXR_OPERATOR_OR           , r'\|\|'          )(__basic)

    # ---

    assign_equal     = __(TokenType.LXR_ASSIGN_EQUAL    , r'=(?!=)')(__basic)
    assign_ref       = __(TokenType.LXR_ASSIGN_REF      , r'<=>'   )(__basic)
    assign_add       = __(TokenType.LXR_ASSIGN_ADD      , r'\+='   )(__basic)
    assign_sub       = __(TokenType.LXR_ASSIGN_SUB      , r'-='    )(__basic)
    assign_times     = __(TokenType.LXR_ASSIGN_TIMES    , r'\*='   )(__basic)
    assign_div       = __(TokenType.LXR_ASSIGN_DIV      , r'/='    )(__basic)
    assign_mod       = __(TokenType.LXR_ASSIGN_MOD      , r'%='    )(__basic)
    assign_text_join = __(TokenType.LXR_ASSIGN_TEXT_JOIN, r'\^='   )(__basic)