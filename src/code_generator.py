from structures import Variable, Link, Link_T, Array


class CodeGenerator:
    def __init__(self):
        self.procedure_table = None
        self.procedure = None

        self.commands = []
        self.symbols = {}
        self.code = []
        self.links = []

        self.first_line = 0 
        self.loop_depth = 0

        self.reg_address = "h"
        self.reg_value = "g"

    def gen_procedure_code(self, name, procedure_table):
        self.procedure_table = procedure_table
        self.procedure = procedure_table[name]
        self.commands = self.procedure.commands
        self.symbols = self.procedure.symbols
        self.links = self.procedure.links
        self.code = []
        self.first_line = procedure_table.current_line
        self.gen_code_from_commands(self.commands)
        if name == 'PROGRAM':
            self.code.append("HALT")
        else:
            self.gen_jump_back(self.procedure.memory_offset)

    def gen_jump_back(self, memory_offset):
        self.gen_const(value=memory_offset, reg="a")
        self.code.append("LOAD a")
        self.code.append("JUMPR a")

    def get_current_line(self, offset = True):
        if offset:
            return self.first_line + len(self.code)
        return len(self.code)

    def gen_code_from_commands(self, commands):
        for command in commands:
            try:
                match command[0]:
                    case "write":
                        self.perform_write(command[1])
                    case "read":
                        self.perform_read(command[1])
                    case "assign":
                        self.perform_assign(command[1], command[2])
                    case "if":
                        self.perform_if(command[1], command[2])
                    case "ifelse":
                        self.perform_if_else(command[1], command[2], command[3])
                    case "while":
                        self.perform_while(command[1], command[2])
                    case "until":
                        self.perform_until(condition=command[1], commands=command[2])
                    case "proc_call":
                        self.perform_procedure(command[1])
            except Exception as e:
                raise Exception(f'{e}, at line {command[-1]}') from None

    # START commands

    def perform_write(self, value):
        if value[0] == "const":
            self.gen_const(value[1], 'a')
        else:
            self.load_variable(value[1], 'a')

        self.code.append("WRITE")

    def perform_read(self, target):
        self.load_address(target, out_reg=self.reg_address, isInit=True)
        self.code.append("READ")
        self.code.append(f"STORE {self.reg_address}")
 
    def perform_assign(self, target, expr):
        self.calculate_expression(expr)
        self.code.append("PUT d")
        self.load_address(target, out_reg=self.reg_address, isInit=True)
        self.code.append("GET d")
        self.code.append(f"STORE {self.reg_address}")

    def perform_if(self, condition, commands):
        cond = self.simplify_condition(condition)
        if isinstance(cond, bool):
            if cond:
                self.gen_code_from_commands(commands)
        else:
            cond_start = self.get_current_line()
            self.check_condition(condition)
            command_start = self.get_current_line()
            self.gen_code_from_commands(commands)
            command_end = self.get_current_line()
            for i in range(cond_start - self.first_line, command_start - self.first_line):
                self.code[i] = self.code[i].replace('finish', str(command_end))

    def perform_if_else(self, condition, commands_if, commands_else):
        cond = self.simplify_condition(condition)
        if isinstance(cond, bool):
            if cond:
                self.gen_code_from_commands(commands_if)
            else:
                self.gen_code_from_commands(commands_else)
        else:
            cond_start = self.get_current_line()
            local_cond_start = cond_start - self.first_line
            self.check_condition(condition)
            if_start = self.get_current_line()
            local_if_start = if_start - self.first_line
            self.gen_code_from_commands(commands_if)
            self.code.append(f"JUMP finish")
            else_start = self.get_current_line()
            local_else_start = else_start - self.first_line
            self.gen_code_from_commands(commands_else)
            command_end = self.get_current_line()
            self.code[local_else_start - 1] = self.code[local_else_start - 1].replace('finish', str(command_end))
            for i in range(local_cond_start, local_if_start):
                self.code[i] = self.code[i].replace('finish', str(else_start))

    def perform_while(self, condition, commands):
        cond = self.simplify_condition(condition)
        if isinstance(cond, bool):
            if cond:
                loop_start = self.get_current_line()
                self.loop_depth += 1
                self.gen_code_from_commands(commands)
                self.loop_depth -= 1
                self.code.append(f"JUMP {loop_start}")
        else:
            cond_start = self.get_current_line()
            local_cond_start = cond_start - self.first_line
            self.check_condition(condition)
            loop_start = self.get_current_line()
            local_loop_start = loop_start - self.first_line
            self.loop_depth += 1
            self.gen_code_from_commands(commands)
            self.loop_depth -= 1
            self.code.append(f"JUMP {cond_start}")
            loop_end = self.get_current_line()
            for i in range(local_cond_start, local_loop_start):
                self.code[i] = self.code[i].replace('finish', str(loop_end))

    def perform_until(self, condition, commands):
        loop_start = self.get_current_line()
        self.loop_depth += 1
        self.gen_code_from_commands(commands)
        self.loop_depth -= 1
        cond_start = self.get_current_line()
        local_cond_start = cond_start - self.first_line
        self.check_condition(condition)
        cond_end = self.get_current_line()
        local_cond_end = cond_end - self.first_line
        for i in range(local_cond_start, local_cond_end):
            self.code[i] = self.code[i].replace('finish', str(loop_start))

    def perform_procedure(self, procedure_call, address_reg="e"):
        procedure_name = procedure_call[0]
        procedure_vars = procedure_call[1]
        if procedure_name not in self.procedure_table:
            raise Exception(f"Undeclared procedure {procedure_name}")
        procedure = self.procedure_table[procedure_name]
        procedure_offset = procedure.memory_offset

        if len(procedure_vars) != len(procedure.links):
            raise Exception(f"Procedure takes {len(procedure.links)} arguments, you give {len(procedure_vars)}")
        
        current_offset = procedure_offset + 1

        for var in procedure_vars:
            self.gen_const(value=current_offset, reg='a')
            self.code.append(f"PUT {address_reg}")

            if var[0] == "load":
                self.load_address(var[1], out_reg='a')
                
                name, link = procedure.get_link_by_offset(current_offset)
                link_type = 'Array' if type(link) is Link_T else 'Var'
                if var[1] in self.symbols:
                    var_type = 'Array' if type(self.symbols[var[1]]) is Array else 'Var'
                elif var[1] in self.links:
                    var_type = 'Array' if type(self.links[var[1]]) is Link_T else 'Var'
                else:
                    raise Exception(f"Undeclared variable {var[1]}")

                if link_type != var_type:
                    raise Exception(f"Using wrong type of variable in arguments, call {procedure_name}")

                if link_type == 'Var' and link.initialized:
                    if var[1] in self.symbols:
                        self.symbols[var[1]].initialized = link.initialized
                    elif var[1] in self.links:
                        self.links[var[1]].initialized = link.initialized
            else:
                Exception("PROCEDURE CALL ERROR")
            
            self.code.append(f"STORE {address_reg}")

            current_offset += 1
        
        self.gen_const(4, 'b')
        self.gen_const(procedure_offset, 'a')
        self.code.append(f"PUT {address_reg}")
        self.code.append("STRK a")
        self.code.append("ADD b")
        self.code.append(f"STORE {address_reg}")

        self.code.append(f"JUMP {procedure.first_line}")
                
    # END commands 

    # START WORK WITH MEMORY
    def load_address(self, target, out_reg="", isInit=False):
        if not out_reg:
            out_reg = self.reg_address
        
        if type(target) is tuple:
            if target[0] == "undeclared":
                raise Exception(f"Undeclared variable {target[0]}")
            elif target[0] == "array":
                self.load_from_array_memory(target[1], target[2], out_reg)
            elif target[0] == "link_t":
                self.load_link_T_address(target[1], target[2], out_reg)
            else:
                raise Exception("LOAD ADDRESS ERROR")
        else:
            if target in self.links:
                if type(self.links[target]) is Link:
                    self.load_link_address(target, out_reg)
                    self.links[target].isUsed = True
                    if isInit:
                        self.links[target].initialized = True
                elif type(self.links[target]) is Link_T:
                    self.load_link_T_address(target, 0, out_reg)
            elif target in self.symbols:
                if type(self.symbols[target]) is Variable:
                    address = self.procedure.get_address(target)
                    self.gen_const(address, out_reg)
                    if isInit:
                        self.symbols[target].initialized = True
                elif type(self.symbols[target]) is Array:
                    self.load_from_array_memory(target, 0, out_reg)
            else:
                raise Exception(f"Array {target} doesn't have index")

    def load_link_T(self, array_name, index, reg=''):
        if not reg:
            reg = self.reg_value
        self.load_link_T_address(array_name, index, reg)
        self.code.append(f"LOAD {reg}")
        if reg != 'a':
            self.code.append(f"PUT {reg}")
                    
    def load_link_T_address(self, array_name, index, out_reg='', reg_f='f'):
        if not out_reg:
            out_reg = self.reg_address
        if type(index) is int:
            address, index = self.procedure.get_address((array_name, index))
            self.gen_const(address, 'a')
            self.code.append("LOAD a")
            self.gen_const(index, reg_f)
            self.code.append(f"ADD {reg_f}")
            if out_reg != 'a':
                self.code.append(f"PUT {out_reg}")
            return
        elif type(index) != tuple:
            raise Exception("LINK_T LOAD ERROR")
        
        if index[1] in self.symbols and type(self.symbols[index[1]]) is Variable:
            if not self.symbols[index[1]].initialized:
                raise Exception(f"Trying to use unitialized variable {index[1]} as index")
            self.load_variable(index[1], out_reg=reg_f)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, 'a')
            self.code.append(f"LOAD a")
            self.code.append(f"ADD {reg_f}")

        elif index[1] in self.links and type(self.links[index[1]]) is Link:
            self.load_link(index[1], out_reg=reg_f)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, 'a')
            self.code.append(f"LOAD a")
            self.code.append(f"ADD {reg_f}")

        if out_reg != 'a':
            self.code.append(f"PUT {out_reg}")

    def load_variable(self, variable, out_reg):
        if type(variable) is tuple:
            if variable[0] == "undeclared":
                raise Exception(f"Undeclared variable {variable[1]}")
            elif variable[0] == "array":
                self.load_array_at(variable[1], variable[2], out_reg)
            elif variable[0] == "link_t":
                self.load_link_T(variable[1], variable[2], out_reg)
            else:
                raise Exception("LOAD VARIABLE ERROR")
        else:
            if variable in self.links and type(self.links[variable]) is Link:
                self.load_link(variable, out_reg)
                self.links[variable].isUsed = True
            elif variable in self.symbols and type(self.symbols[variable]) is Variable:
                var = self.procedure.get_variable(variable)
                if not var.initialized:
                    if self.loop_depth == 0:
                        raise Exception(f"Uninitialized variable {variable}")
                    else:
                        print(f"WARNING: variable {variable} may be used before set")               
                self.load_from_memory(var.memory_offset, out_reg)

    def load_link(self, name, out_reg=''):
        if not out_reg:
            out_reg = self.reg_value
        address = self.procedure.get_address(name)
        self.gen_const(address, out_reg)
        self.code.append(f"LOAD {out_reg}")
        self.code.append("LOAD a")
        if out_reg != 'a':
            self.code.append(f"PUT {out_reg}")

    def load_link_address(self, name, out_reg=''):
        if not out_reg:
            out_reg = self.reg_value
        address = self.procedure.get_address(name)
        self.gen_const(address, out_reg)
        self.code.append(f"LOAD {out_reg}")
        if out_reg != 'a':
            self.code.append(f"PUT {out_reg}")

    def load_from_memory(self, address, out_reg=""):
        self.gen_const(address, self.reg_address)
        self.code.append(f"LOAD {self.reg_address}")
        if out_reg:
            self.code.append(f"PUT {out_reg}")
    
    def load_array_at(self, array_name, index, reg=""):
        if not reg:
            reg = self.reg_value
        self.load_from_array_memory(array_name, index, reg)
        self.code.append(f"LOAD {reg}")
        if reg != 'a':
            self.code.append(f'PUT {reg}')

    def load_from_array_memory(self, array_name, index, target_reg, reg2='f'):
        if type(index) is int:
            address = self.procedure.get_address((array_name, index))
            self.gen_const(address, target_reg)
        elif type(index) is tuple:
            if index[1] in self.symbols and type(self.symbols[index[1]]) is Variable:
                if not self.symbols[index[1]].initialized:
                    raise Exception(f"Trying to use {array_name}[{index[1]}] where variable {index[1]} is uninitialized")
                self.load_from_memory(self.procedure.get_address(index[1]), reg2)
                arr = self.procedure.get_variable(array_name)
                self.gen_const(arr.memory_offset, 'a')
                self.code.append(f"ADD {reg2}")
            elif index[1] in self.links and type(self.links[index[1]]) is Link:
                self.load_link(index[1], reg2)
                arr = self.procedure.get_variable(array_name)
                self.gen_const(arr.memory_offset, 'a')
                self.code.append(f"ADD {reg2}")
            if target_reg != 'a':
                self.code.append(f"PUT {target_reg}")

    def gen_const(self, value, reg):
        self.code.append(f"RST {reg}")
        bits = bin(value)[2:]
        for bit in bits[:-1]:
            if bit == '1':
                self.code.append(f"INC {reg}")
            self.code.append(f"SHL {reg}")
        if bits[-1] == '1':
            self.code.append(f"INC {reg}")

    # END WORK WITH MEMORY

    def calculate_expression(self, expr, first='a', second='b'):
        match expr[0]:
            case "const":
                self.gen_const(expr[1], self.reg_value)
                self.code.append(f"GET {self.reg_value}")
                if first != 'a':
                    self.code.append(f"PUT {first}")
            case "load":
                self.load_variable(expr[1], first)
            case "add":
                const = False
                if expr[1][0] == 'const' and expr[2][0] != 'const':
                    expr = (expr[0], expr[2], expr[1])
                    const = True
                elif expr[2][0] == 'const':
                    const = True
                self.adding_case(expr1=expr[1], expr2=expr[2], const=const, buf_reg=second)
                if first != 'a':
                    self.code.append(f"PUT {first}")
            case "sub":
                self.subtraction_case(expr1=expr[1], expr2=expr[2], buf_reg=second)
                if first != 'a':
                    self.code.append(f"PUT {first}")
            case "mul":
                const = False
                if expr[1][0] == 'const' and expr[2][0] != 'const':
                    expr = (expr[0], expr[2], expr[1])
                    const = True
                elif expr[2][0] == 'const':
                    const = True
                self.multiplication_case(expr1=expr[1], expr2=expr[2], const=const)
                if first != 'a':
                    self.code.append(f"PUT {first}")
            case "div":
                self.division_case(expr1=expr[1], expr2=expr[2])
                if first != 'a':
                    self.code.append(f"PUT {first}")
            case "mod":
                self.mod_case(expr1=expr[1], expr2=expr[2])

    def adding_case(self, expr1, expr2, const, buf_reg):
        if expr1[0] == expr2[0] == 'const':
            self.gen_const(expr1[1] + expr2[2], 'a')
        elif expr1 == expr2:
            self.calculate_expression(expr1)
            self.code.append("SHL a")
        elif const:
            self.calculate_expression(expr1)
            change = f"INC a"
            self.code += expr2[1] * [change]
        else:
            self.calculate_expression(expr2, buf_reg)
            self.calculate_expression(expr1)
            self.code.append(f"ADD {buf_reg}")

    def subtraction_case(self, expr1, expr2, buf_reg):
        if expr1[0] == expr2[0] == 'const':
            val = max(0, expr1[1] - expr2[1])
            if val:
                self.gen_const(val, 'a')
            else:
                self.code.append("RST a")
        elif expr1[0] == "const" or expr2[0] == "const":
            if expr2[0] == "const":
                if expr2[1] < 12:
                    self.calculate_expression(expr1)
                    change = "DEC a"
                    self.code += expr2[1] * [change]
                    return
            elif expr1[0] == "const":
                if expr1[1] == 0:
                    self.code.append("RST a")
                    return

        self.calculate_expression(expr1, buf_reg)
        self.calculate_expression(expr2, "c")
        self.code.append(f"GET {buf_reg}")
        self.code.append("SUB c")

    def multiplication_case(self, expr1, expr2, const, second_reg="b", third_reg="c", temp_res_reg="d"):
        if expr1[0] == expr2[0] == "const":
            self.calculate_expression(expr1[1] * expr2[1])
            return
        if const:
            val = expr2[1]
            if val == 0:
                self.code.append("RESET a")
                return
            elif val == 1:
                self.calculate_expression(expr1)
                return
            elif val & (val - 1) == 0:
                self.calculate_expression(expr1)
                while val > 1:
                    self.code.append(f"SHL a")
                    val /= 2
                return
        if expr1 == expr2:
            self.calculate_expression(expr1)
            self.code.append(f"PUT {second_reg}")
            self.code.append(f"PUT {third_reg}")
        else:
            self.calculate_expression(expr2, third_reg)
            self.calculate_expression(expr1, second_reg)

        first_line = self.get_current_line() - 1
        self.code.append(f"RST {temp_res_reg}") 
        self.code.append(f"GET {third_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS {first_line + 21}")
        self.code.append(f"JUMP {first_line + 8}")

        self.code.append(f"SHL {second_reg}")  
        self.code.append(f"SHR {third_reg}")

        self.code.append(f"GET {third_reg}")  
        self.code.append(f"JZERO {first_line + 32}")  
        self.code.append(f"SHR {third_reg}")
        self.code.append(f"SHL {third_reg}")
        self.code.append(f"SUB {third_reg}")
        self.code.append(f"JPOS {first_line + 15}")
        self.code.append(f"JUMP {first_line + 6}")

        self.code.append(f"GET {temp_res_reg}")  
        self.code.append(f"ADD {second_reg}")
        self.code.append(f"PUT {temp_res_reg}")
        self.code.append(f"JUMP {first_line + 6}")

        self.code.append(f"SHL {third_reg}")  
        self.code.append(f"SHR {second_reg}")

        self.code.append(f"GET {second_reg}")  
        self.code.append(f"JZERO {first_line + 32}") 
        self.code.append(f"SHR {second_reg}")
        self.code.append(f"SHL {second_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS {first_line + 28}")
        self.code.append(f"JUMP {first_line + 19}")

        self.code.append(f"GET {temp_res_reg}")  
        self.code.append(f"ADD {third_reg}")
        self.code.append(f"PUT {temp_res_reg}")
        self.code.append(f"JUMP {first_line + 19}") 

        self.code.append(f"GET d") 

    def division_case(
            self, expr1, expr2,
            ismod = False,
            r_a='a',
            dividend_reg="b",
            divisor_reg="c",
            quotient_reg="d",
            remainder_reg="e",
    ):
        if not ismod:
            if expr1[0] == expr2[0] == "const":
                if expr2[1] > 0:
                    self.gen_const(expr1[1] // expr2[1], r_a)
                else:
                    self.code.append(f"RST {r_a}")
            elif expr1 == expr2:
                self.calculate_expression(expr1)
                self.code.append(f"JZERO {self.get_current_line() + 2}")
                self.code.append(f"INC {r_a}")
            elif expr1[0] == "const" and expr1[1] == 0:
                self.code.append(f"RST {r_a}")
            elif expr2[0] == "const":
                val = expr2[1]
                if val == 0:
                    self.code.append(f"RST {r_a}")
                    return
                elif val == 1:
                    self.calculate_expression(expr1)
                    return
                elif val & (val - 1) == 0:
                    self.calculate_expression(expr1)
                    while val > 1:
                        self.code.append(f"SHR {r_a}")
                        val /= 2
                    return
                
        self.calculate_expression(expr1, dividend_reg)
        self.calculate_expression(expr2, divisor_reg)

        first_line = self.get_current_line() - 1
        self.code.append(f"RST {quotient_reg}")          
        self.code.append(f"RST {remainder_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"JZERO {first_line + 37}")     
        self.code.append(f"GET {dividend_reg}")          
        self.code.append(f"PUT {remainder_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"PUT {dividend_reg}")
        self.code.append(f"GET {remainder_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JZERO {first_line + 19}")
        self.code.append(f"GET {dividend_reg}")          
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 17}")
        self.code.append(f"SHR {dividend_reg}")
        self.code.append(f"JUMP {first_line + 19}")
        self.code.append(f"SHL {dividend_reg}")         
        self.code.append(f"JUMP {first_line + 12}")

        self.code.append(f"GET {dividend_reg}")         
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 23}")
        self.code.append(f"JUMP {first_line + 37}")    
        self.code.append(f"GET {remainder_reg}")        
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"PUT {remainder_reg}")
        self.code.append(f"INC {quotient_reg}")

        self.code.append(f"GET {dividend_reg}")         
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 19}")
        self.code.append(f"SHR {dividend_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JZERO {first_line + 35}")
        self.code.append(f"JUMP {first_line + 37}")
        self.code.append(f"SHL {quotient_reg}")         
        self.code.append(f"JUMP {first_line + 27}")
        if ismod:
            self.code.append(f"GET {remainder_reg}")
        else:
            self.code.append(f"GET {quotient_reg}")

    def mod_case(self, expr1, expr2):
        if expr1 == expr2:
            self.code.append("RST a")
            return
        elif expr1[0] == expr2[0] == "const":
            self.calculate_expression(expr1[1] % expr2[1])
        elif expr1[0] == "const" and expr1[1] == 0:
            self.code.append("RST a")
            return
        elif expr2[0] == "const":
            val = expr2[1]
            if val < 2:
               self.code.append("RST a")
            elif val == 2:
                self.calculate_expression(expr1) 
                self.code.append("PUT b")
                self.code.append("SHR b")
                self.code.append("SHL b")
                self.code.append("SUB b")
        self.division_case(expr1=expr1, expr2=expr2, ismod=True)

    def simplify_condition(self, condition):
        if condition[1][0] == "const" and condition[2][0] == "const":
            if condition[0] == "le":
                return condition[1][1] <= condition[2][1]
            elif condition[0] == "ge":
                return condition[1][1] >= condition[2][1]
            elif condition[0] == "lt":
                return condition[1][1] < condition[2][1]
            elif condition[0] == "gt":
                return condition[1][1] > condition[2][1]
            elif condition[0] == "eq":
                return condition[1][1] == condition[2][1]
            elif condition[0] == "ne":
                return condition[1][1] != condition[2][1]

        elif condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "le":
                return True
            elif condition[0] == "gt":
                return False
            else:
                return condition

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "ge":
                return True
            elif condition[0] == "lt":
                return False
            else:
                return condition

        elif condition[1] == condition[2]:
            if condition[0] in ["ge", "le", "eq"]:
                return True
            else:
                return False

        else:
            return condition

    def check_condition(self, condition, first_reg='a', second_reg='b', third_reg='c'):
        if condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "ge" or condition[0] == "eq":
                self.calculate_expression(condition[2])
                self.code.append(f"JZERO {self.get_current_line() + 2}") 
                self.code.append("JUMP finish")

            elif condition[0] == "lt" or condition[0] == "ne":
                self.calculate_expression(condition[2])
                self.code.append(f"JZERO finish")

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "le" or condition[0] == "eq":
                self.calculate_expression(condition[1])
                self.code.append(f"JZERO {self.get_current_line() + 2}")  
                self.code.append("JUMP finish")

            elif condition[0] == "gt" or condition[0] == "ne":
                self.calculate_expression(condition[1])
                self.code.append(f"JZERO finish")
        else:
            self.calculate_expression(condition[1], second_reg)
            self.calculate_expression(condition[2], third_reg)

            if condition[0] == "le":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO {self.get_current_line() + 2}") 
                self.code.append(f"JUMP finish")

            elif condition[0] == "ge":
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO {self.get_current_line() + 2}")  
                self.code.append(f"JUMP finish")

            elif condition[0] == "lt":
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO finish")

            elif condition[0] == "gt":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO finish")

            elif condition[0] == "eq":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO {self.get_current_line() + 2}") 
                self.code.append(f"JUMP finish")

                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO {self.get_current_line() + 2}") 
                self.code.append(f"JUMP finish")

            elif condition[0] == "ne":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO {self.get_current_line() + 2}")
                self.code.append(f"JUMP {self.get_current_line() + 3}")
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO finish")
