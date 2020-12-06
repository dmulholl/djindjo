import re


# We use this error type for reporting lexing and parsing errors.
class TemplateError(Exception):
    pass


# The Template class is the engine's public interface.
class Template:

    def __init__(self, template_string):
        self.root_node = Parser(template_string).parse()

    def render(self, data_dict):
        return self.root_node.render(Context(data_dict))


# A Context object is a wrapper around the user's input data. Its `.lookup()`
# method contains the lookup-logic for resolving dotted variable names.
class Context:

    def __init__(self, data_dict):
        self.stack = [data_dict]

    def __setitem__(self, key, value):
        self.stack[-1][key] = value

    def __getitem__(self, key):
        for stack_dict in reversed(self.stack):
            if key in stack_dict:
                return stack_dict[key]
        raise KeyError(key)

    def push(self):
        self.stack.append({})

    def pop(self):
        self.stack.pop()

    def lookup(self, keystring):
        result = self
        for token in keystring.split('.'):
            try:
                result = result[token]
            except:
                try:
                    result = getattr(result, token)
                except:
                    result = None
                    break
        return result


# Tokens come in three different types: "text", "print", and "instruction".
class Token:

    def __init__(self, token_type, text):
        self.type = token_type
        self.text = text

    def __str__(self):
        return f"({repr(self.type)}, {repr(self.text)})"

    @property
    def keyword(self):
        return self.text.split()[0]


# The Lexer takes an input template string and chops it into a list of Tokens.
class Lexer:

    def __init__(self, template_string):
        self.template_string = template_string
        self.tokens = []
        self.index = 0

    def tokenize(self):
        while self.index < len(self.template_string):
            if self.match("{#"):
                self.read_comment_tag()
            elif self.match("{{"):
                self.read_print_tag()
            elif self.match("{%"):
                self.read_instruction_tag()
            else:
                self.read_text()
        return self.tokens

    def match(self, target):
        if self.template_string.startswith(target, self.index):
            return True
        return False

    def read_comment_tag(self):
        self.index += 2
        while self.index < len(self.template_string) - 1:
            if self.match("#}"):
                self.index += 2
                return
            self.index += 1
        raise TemplateError("unclosed comment tag")

    def read_print_tag(self):
        self.index += 2
        start_index = self.index
        while self.index < len(self.template_string) - 1:
            if self.match("}}"):
                text = self.template_string[start_index:self.index].strip()
                self.tokens.append(Token("print", text))
                self.index += 2
                return
            self.index += 1
        raise TemplateError("unclosed print tag")

    def read_instruction_tag(self):
        self.index += 2
        start_index = self.index
        while self.index < len(self.template_string) - 1:
            if self.match("%}"):
                text = self.template_string[start_index:self.index].strip()
                self.tokens.append(Token("instruction", text))
                self.index += 2
                return
            self.index += 1
        raise TemplateError("unclosed instruction tag")

    def read_text(self):
        start_index = self.index
        while self.index < len(self.template_string):
            if self.match("{#") or self.match("{{") or self.match("{%"):
                break
            self.index += 1
        text = self.template_string[start_index:self.index]
        self.tokens.append(Token("text", text))


# A compiled template is a tree of Node instances. The entire node tree can be
# rendered by calling `.render()` on the root node.
class Node:

    def __init__(self, token=None):
        self.token = token
        self.children = []

    def __str__(self):
        return self.to_str()

    def render(self, context):
        return "".join(child.render(context) for child in self.children)

    def to_str(self, depth=0):
        output = ["·  " * depth + f"{self.__class__.__name__}"]
        for child in self.children:
            output.append(child.to_str(depth + 1))
        return "\n".join(output)

    def process_children(self):
        pass


# TextNodes represent ordinary template text, i.e. text not enclosed in tag
# delimiters.
class TextNode(Node):

    def render(self, context):
        return self.token.text


# PrintNodes represent print tags, e.g `{{ dotted.varname }}`.
class PrintNode(Node):

    def render(self, context):
        value = context.lookup(self.token.text)
        if value is None:
            return ""
        return str(value)


# IfNodes implement conditional branching.
class IfNode(Node):

    regex = re.compile(r"^if\s+([\w.]+)$")

    def __init__(self, token):
        super().__init__(token)
        if (match := self.regex.match(token.text)):
            self.arg_string = match.group(1)
        else:
            raise TemplateError("malformed {% if %} tag")
        self.true_branch = Node()
        self.false_branch = Node()

    def render(self, context):
        value = context.lookup(self.arg_string)
        if value:
            return self.true_branch.render(context)
        else:
            return self.false_branch.render(context)

    def process_children(self):
        branch = self.true_branch
        for child in self.children:
            if isinstance(child, ElseNode):
                branch = self.false_branch
            else:
                branch.children.append(child)

    def to_str(self, depth=0):
        output = ["·  " * depth + f"{self.__class__.__name__}"]
        output.append(self.true_branch.to_str(depth + 1))
        output.append(self.false_branch.to_str(depth + 1))
        return "\n".join(output)


# An ElseNode acts as a placeholder, allowing us to split an IfNode's children
# into true and false branches.
class ElseNode(Node):
    pass


# ForNodes implement `for ... in ...` looping over iterables.
class ForNode(Node):

    regex = re.compile(r"^for\s+(\w+)\s+in\s+([\w.]+)$")

    def __init__(self, token):
        super().__init__(token)
        if (match := self.regex.match(token.text)):
            self.var_name = match.group(1)
            self.arg_string = match.group(2)
        else:
            raise TemplateError("malformed {% for %} tag")

    def render(self, context):
        output = []
        collection = context.lookup(self.arg_string)
        if hasattr(collection, '__iter__'):
            context.push()
            for item in collection:
                context[self.var_name] = item
                output.append("".join(child.render(context) for child in self.children))
            context.pop()
        return "".join(output)


# The Parser takes an input template string, lexes it into a token stream, then
# compiles the token stream into a tree of nodes.
class Parser:

    keywords = {
        "if": (IfNode, "endif"),
        "else": (ElseNode, None),
        "for": (ForNode, "endfor"),
    }

    endwords = ["endif", "endfor"]

    def __init__(self, template_string):
        self.template_string = template_string

    def parse(self):
        stack = [Node()]
        expecting = []

        for token in Lexer(self.template_string).tokenize():
            if token.type == "text":
                stack[-1].children.append(TextNode(token))
            elif token.type == "print":
                stack[-1].children.append(PrintNode(token))
            elif token.keyword in self.keywords:
                node_class, endword = self.keywords[token.keyword]
                node = node_class(token)
                stack[-1].children.append(node)
                if endword:
                    stack.append(node)
                    expecting.append(endword)
            elif token.keyword in self.endwords:
                if len(expecting) == 0:
                    raise TemplateError(f"unexpected {token.keyword}")
                elif expecting[-1] != token.keyword:
                    raise TemplateError(f"expected {expecting[-1]}, found {token.keyword}")
                else:
                    stack[-1].process_children()
                    stack.pop()
                    expecting.pop()
            else:
                raise TemplateError(f"illegal instruction '{token.keyword}'")

        if expecting:
            raise TemplateError(f"expecting {expecting[-1]}")

        return stack.pop()

