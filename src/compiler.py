from sly import Lexer, Parser
from structures import Procedure, Array, Variable, Link, Link_T
from procedures_table import ProcedureList
import sys


class ImpLexer(Lexer):
    tokens = {PROGRAM, PROCEDURE, IS, IN, END, PID, NUM, IF, THEN, ELSE, ENDIF, WHILE, DO, ENDWHILE, REPEAT, UNTIL,
              READ, WRITE, EQ, NEQ, GT, LT, GEQ, LEQ, GETS, T}
    literals = {'+', '-', '*', '/', '%', ',', ':', ';', '(', ')', '[', ']'}
    ignore = ' \t'

    @_(r'#.*')
    def ignore_comment(self, t):
        self.lineno += t.value.count('\n')

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    PROGRAM = r"PROGRAM"
    PROCEDURE = r"PROCEDURE"
    IS = r"IS"
    IN = r"IN"

    ENDWHILE = r"ENDWHILE"
    ENDIF = r"ENDIF"
    END = r"END"

    WHILE = r"WHILE"
    IF = r"IF"

    THEN = r"THEN"
    ELSE = r"ELSE"
    DO = "DO"

    REPEAT = r"REPEAT"
    UNTIL = r"UNTIL"

    READ = r"READ"
    WRITE = r"WRITE"

    GETS = r":="
    NEQ = r"!="
    GEQ = r">="
    LEQ = r"<="
    EQ = r"="
    GT = r">"
    LT = r"<"
    PID = r"[_a-z]+"

    T = r"T"

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    def error(self, t):
        raise Exception(f"Illegal character '{t.value[0]}'")


class ImpParser(Parser):
    tokens = ImpLexer.tokens
    procedures_table = ProcedureList()
    curr_procedure = Procedure(1)
    code = None
    consts = set()

    @_('procedures main')
    def program_all(self, p):
        return self.procedures_table

    @_('procedures PROCEDURE procedure_init IS declarations IN commands END', 'procedures PROCEDURE procedure_init IS IN commands END')
    def procedures(self, p):
        self.curr_procedure.set_commands(p.commands)
        self.procedures_table.add_procedure(self.curr_procedure)

    @_('')
    def procedures(self, p):
        pass

    @_('PID "(" procedure_args ")"')
    def procedure_init(self, p):
        self.curr_procedure.name = p[0]

    @_('PID "(" args ")"')
    def procedure_call(self, p):
        if p[0] == self.curr_procedure.name:
            raise Exception(f"Impossible to call function {p[0]} inside itself, line {p.lineno}")
        elif p[0] in self.procedures_table:
            return p[0], p[2]
        else:
            raise Exception(f"Undeclaired function {p[0]}, line {p.lineno}")

    @_('program IS declarations IN commands END', 'program IN commands END')
    def main(self, p):
        self.curr_procedure.set_commands(p.commands)
        self.procedures_table.add_procedure(self.curr_procedure)

    @_('PROGRAM')
    def program(self, p):
        self.curr_procedure = Procedure(self.procedures_table.memory_offset)
        self.curr_procedure.name = "PROGRAM"

    # START DECLARATIONS
    @_('declarations "," PID', 'PID')
    def declarations(self, p):
        self.curr_procedure.add_variable(p[-1])

    @_('declarations "," PID "[" NUM "]" ')
    def declarations(self, p):
        self.curr_procedure.add_array(p[2], p[4])

    @_('PID "[" NUM "]"')
    def declarations(self, p):
        self.curr_procedure.add_array(p[0], p[2])

    # END DECLARATIONS

    # START OF ANALYZING PROCEDURE ARGUMENTS
    @_('procedure_args "," PID')
    def procedure_args(self, p):
        self.curr_procedure.add_link(p[2])

    @_('procedure_args "," T PID')
    def procedure_args(self, p):
        self.curr_procedure.add_link_T(p[3])

    @_('PID')
    def procedure_args(self, p):
        self.curr_procedure = Procedure(self.procedures_table.memory_offset)
        self.curr_procedure.add_link(p[0])

    @_('T PID')
    def procedure_args(self, p):
        self.curr_procedure = Procedure(self.procedures_table.memory_offset)
        self.curr_procedure.add_link_T(p[1])

    # END OF ANALYZING PROCEDURE ARGUMENTS     
        
    # START ANALYZING OF PROCEDURE ARGUMENTS(CALL)

    @_('args "," PID')   
    def args(self, p):
        if p[2] in self.curr_procedure.symbols:
            return p[0] + [("load", p[2])]
        elif p[2] in self.curr_procedure.links:
            return p[0] + [("load", p[2])]
        else:
            raise Exception(f"Undeclared variable {p[2]}, line {p.lineno}")
        
    @_('PID')
    def args(self, p):
        if p[0] in self.curr_procedure.symbols:
            return [("load", p[0])]
        elif p[0] in self.curr_procedure.links:
            return [("load", p[0])]
        else:
            raise Exception(f"Undeclared variable {p[0]}, line {p.lineno}")

    # END OF PROCEDURE ARGUMENTS(CALL)

    @_('commands command')
    def commands(self, p):
        return p[0] + [p[1]]

    @_('command')
    def commands(self, p):
        command = list(p[0])
        command.append(p.lineno)
        return [tuple(command)]

    @_('identifier GETS expression ";"')
    def command(self, p):
        return "assign", p[0], p[2], p.lineno

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        resp = "ifelse", p[1], p[3], p[5], self.consts.copy(), p.lineno
        self.consts.clear()
        return resp

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        resp = "if", p[1], p[3], self.consts.copy(), p.lineno
        self.consts.clear()
        return resp

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        resp = "while", p[1], p[3], self.consts.copy(), p.lineno
        self.consts.clear()
        return resp

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        return "until", p[3], p[1], p.lineno

    @_('READ identifier ";"')
    def command(self, p):
        return "read", p[1]

    @_('WRITE value ";"')
    def command(self, p):
        if p[1][0] == "const":
            self.consts.add(int(p[1][1]))
        return "write", p[1]

    @_('procedure_call ";"')
    def command(self, p):
        return 'proc_call', p[0]

    @_('value')
    def expression(self, p):
        return p[0]

    @_('value "+" value')
    def expression(self, p):
        return "add", p[0], p[2]

    @_('value "-" value')
    def expression(self, p):
        return "sub", p[0], p[2]

    @_('value "*" value')
    def expression(self, p):
        return "mul", p[0], p[2]

    @_('value "/" value')
    def expression(self, p):
        return "div", p[0], p[2]

    @_('value "%" value')
    def expression(self, p):
        return "mod", p[0], p[2]

    @_('value EQ value')
    def condition(self, p):
        return "eq", p[0], p[2]

    @_('value NEQ value')
    def condition(self, p):
        return "ne", p[0], p[2]

    @_('value LT value')
    def condition(self, p):
        return "lt", p[0], p[2]

    @_('value GT value')
    def condition(self, p):
        return "gt", p[0], p[2]

    @_('value LEQ value')
    def condition(self, p):
        return "le", p[0], p[2]

    @_('value GEQ value')
    def condition(self, p):
        return "ge", p[0], p[2]

    @_('NUM')
    def value(self, p):
        return "const", p[0]

    @_('identifier')
    def value(self, p):
        return "load", p[0]

    @_('PID')
    def identifier(self, p):
        if p[0] in self.curr_procedure.symbols:
            if type(self.curr_procedure.symbols[p[0]]) is Variable:
                return p[0]
        elif p[0] in self.curr_procedure.links:
            if type(self.curr_procedure.links[p[0]]) is Link:
                return p[0]
        raise Exception(f"Undeclared variable {p[0]} in {p.lineno} line")
            
    @_('PID "[" NUM "]"')
    def identifier(self, p):
        if p[0] in self.curr_procedure.symbols and type(self.curr_procedure.symbols[p[0]]) is Array:
            return "array", p[0], p[2]
        elif p[0] in self.curr_procedure.links and type(self.curr_procedure.links[p[0]]) is Link_T:
            return "link_t", p[0], p[2]
        else:
            raise Exception(f"Undeclared array {p[0]}, in {p.lineno} line")

    @_('PID "[" PID "]"')
    def identifier(self, p):
        if p[0] in self.curr_procedure.symbols and type(self.curr_procedure.symbols[p[0]]) is Array:
            if p[2] in self.curr_procedure.symbols and type(self.curr_procedure.symbols[p[2]]) is Variable:
                return "array", p[0], ("load", p[2])
            elif p[2] in self.curr_procedure.links and type(self.curr_procedure.links[p[2]]) is Link:
                return "array", p[0], ("load", p[2])
            else:
                raise Exception(f"Undeclared variable {p[2]}, line {p.lineno}")
        elif p[0] in self.curr_procedure.links and type(self.curr_procedure.links[p[0]]) is Link_T:
            if p[2] in self.curr_procedure.symbols and type(self.curr_procedure.symbols[p[2]]) is Variable:
                return "link_t", p[0], ("load", p[2])
            elif p[2] in self.curr_procedure.links and type(self.curr_procedure.links[p[2]]) is Link:
                return "link_t", p[0], ("load", p[2])
            else:
                raise Exception(f"Undeclared variable {p[2]}, line {p.lineno}")
        else:
            raise Exception(f"Undeclared array {p[0]}, line {p.lineno}")

    def error(self, token):
        raise Exception(f"Syntax error: '{token.value}' in line {token.lineno}")


sys.tracebacklimit = 0
lex = ImpLexer()
pars = ImpParser()
with open(sys.argv[1]) as in_f:
    text = in_f.read()

pars.parse(lex.tokenize(text))
code_gen = pars.code
procedures_table = pars.procedures_table

procedures_table.gen_first_jump()
procedures_table.gen_code()
procedures_table.update_first_jump()

with open(sys.argv[2], 'w') as out_f:
    print(procedures_table.first_line, file=out_f) # GENERATE FIRST JUMP   
    for procedure_code in procedures_table.code:
        for line in procedure_code:
            print(line, file=out_f)
