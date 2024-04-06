class Array:
    def __init__(self, name, memory_offset, size):
        self.name = name
        self.memory_offset = memory_offset
        self.size = size

    def get_at(self, index):
        if 0 <= index <= self.size - 1:
            return self.memory_offset + index
        else:
            raise Exception(f"Index {index} out of range for array {self.name}")


class Variable:
    def __init__(self, memory_offset):
        self.memory_offset = memory_offset
        self.initialized = False


class Link:
    def __init__(self, memory_offset):
        self.memory_offset = memory_offset
        self.initialized = False
        self.isUsed = False


class Link_T:
    def __init__(self, memory_offset):
        self.memory_offset = memory_offset

    def get_at(self, index):
        return self.memory_offset, index


class Procedure():
    def __init__(self, memory_offset):
        self.name = ''
        self.memory_offset = memory_offset
        self.last_index = memory_offset + 1
        self.first_line = 0
        self.commands = []
        self.symbols = {}
        self.links = {}
        self.consts = {}

    def set_commands(self, commands):
        self.commands = commands

    def add_variable(self, name):
        if name in self.symbols or name in self.links:
            raise Exception(f"Redeclaration of {name}")
        self.symbols.setdefault(name, Variable(self.last_index))
        self.last_index += 1

    def add_array(self, name, size):
        if name in self.symbols or name in self.links:
            raise Exception(f"Redeclaration of {name}")
        elif size <= 0:
            raise Exception(f"Wrong range in declaration of {name}")
        self.symbols.setdefault(name, Array(name, self.last_index, size))
        self.last_index += size

    def add_link(self, name):
        if name in self.links:
            raise Exception(f"Redeclaration of {name}")
        self.links.setdefault(name, Link(self.last_index))
        self.last_index += 1

    def add_link_T(self, name):
        if name in self.links:
            raise Exception(f"Redeclaration of {name}")
        self.links.setdefault(name, Link_T(self.last_index))
        self.last_index += 1

    def get_variable(self, name):
        if name in self.symbols:
            return self.symbols[name]
        elif name in self.links:
            return self.links[name]
        else:
            raise Exception(f"Undeclared variable {name}")

    def get_array_at(self, name, index):
        if name in self.symbols:
            try:
                return self.symbols[name].get_at(index)
            except AttributeError:
                raise Exception(f"Non-array {name} used as an array")
        elif name in self.links:
            try:
                return self.links[name].get_at(index)
            except AttributeError:
                raise Exception(f"Non-array {name} used as an array")
        else:
            raise Exception(f"Undeclared array {name}")

    def get_address(self, target):
        if type(target) == str:
            return self.get_variable(target).memory_offset
        else:
            return self.get_array_at(target[0], target[1])

    def get_link_by_offset(self, offset):
        for name in self.links:
            if self.links[name].memory_offset == offset:
                return name, self.links[name]
        raise Exception("get_link Error, no such element at links")
