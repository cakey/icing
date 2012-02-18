# TODO
# d |& operator
# d */+
# d num
# d paranthesis
# d *args (tree based on how many args are passed)
# d chaining
# d pull out traverse logic into RelationshipQuery class to it can be
# d     'precompiled' and chained
#   test coverage
#   hamcrest
#   want to query in reverse
#   unit test bad input
#   optimise applying querys to sets
#   optional type safety
#   abstract out dicts/set to let them be backed by anything
#   relationships with more than one root (mutual friends)
#   back the dicts/sets by redis
#   consider the best way to persist dicts/sets
#   'are these two nodes linked by this path'
#   can apply queries to sets (collection extends set, is callable)
#       do we return as dicts or sets?
#   limit on duration
#   track route
#   indexing


import collections
import string
import uuid

class Tree(object):
    def __init__(self, *args, **kwargs):
        self.rev = kwargs.get("rev", False)
        self.op = None
        self.lbranch = None
        self.rbranch = None
        
        if len(args) == 0:
            self.op = 'self'
            return
            
        if len(args) == 1:
            query = args[0]
            if not query:
                self.op = 'self'
                return
                
        if len(args) == 2:
            self.op = args[0]
            self.lbranch = args[1]
            return
            
        if len(args) == 3:
            self.op = args[0]
            self.lbranch = args[1]
            self.rbranch = args[2]
            return 
        
        if query.startswith("!"):
            self.op = "!"
            self.lbranch = Tree(query[1:])
            return
            
        if query.startswith("(") and query.endswith(")"):
            tree = Tree(query[1:-1])
            self.op, self.lbranch, self.rbranch = tree.op, tree.lbranch, tree.rbranch
            return
            
        if "(" in query and ")" in query:
            unmatched=0
            lpos = None
            rpos = None
            for i,c in enumerate(query):
                if c == "(":
                    if unmatched == 0:
                        lpos = i
                    unmatched += 1
                if c ==")":
                    unmatched -= 1
                    if unmatched == 0:
                        rpos = i
                        break
                        
            before = query[0:lpos]
            during = query[lpos:rpos+1]
            after = query[rpos+1:]
            
            if before:
                self.op = "->" if before.endswith("->") else before[-1]
                self.lbranch = before[0:-2] if before.endswith("->") else before[0:-1]
            if after:
                tree = Tree()
                tree.op = "->" if after.startswith("->") else after[0]
                tree.lbranch = during
                tree.rbranch = after[2:] if after.startswith("->") else after[1:]
                self.rbranch = tree
                if not before:
                    self.op, self.lbranch, self.rbranch = tree.op, tree.lbranch, tree.rbranch
            else:
                self.rbranch=during
                
            return
        
        # the order here defines precendence
        for op in ["->", "&", "|"]:
            if op in query:
                self.op = op
                branches = query.split(op)
                self.lbranch = Tree(branches[0])
                self.rbranch = Tree(op.join(branches[1:]))
                return
        
        if query.endswith("*"):
            self.op = "*"
            self.lbranch = Tree(query[0:-1])
            return
            
        if query.endswith("+"):
            self.op = "->"
            tree = Tree(query[0:-1])
            self.lbranch = tree
            self.rbranch = Tree('*', tree)
            return
        
        if query[-1] in string.digits:
            num = int(query[-1])
            if num == 0:
                self.op = "self"
                return
            elif num == 1:
                tree = Tree(query[0:-1])
                self.op, self.lbranch, self.rbranch = tree.op, tree.lbranch, tree.rbranch
                return
            else: 
                tree = Tree(query[0:-1])
                self.op = "->"
                self.lbranch = tree
                self.rbranch = Tree(query[0:-1] + str(num-1))
                return
        
        self.op = "atom"
        self.lbranch = query
            
    def __repr__(self):
        return "%s(%s,%s)" % (self.op, self.lbranch, self.rbranch)
        
    def __call__(self, thing):
        if isinstance(thing, Tree):
            tree = thing
            return Tree('->', tree, self)
        else:
            node = thing
        return node(self)
        
    def __or__(self, other):
        return Tree("|",  self, other)
        
    def __and__(self, other):
        return Tree("&", self, other)
        
    def __getitem__(self, num):
        if num == '*':
            return Tree("*", self)
            
        if num == '+':
            return Tree("->", self, Tree("*", self))
            
        if num == 0:
            return Tree()
        elif num == 1:
            return self
        else:
            return Tree("->", self, self[num-1])
        
    def test(self, first, second):
        # TODO: come at from both outgoing,
        #    or you might as well just use 'in' yourself.
        return second in self(first)
    
    @property    
    def reverse(self):
        rev = not self.rev
        try:
            revlbranch = self.lbranch.reverse
        except AttributeError as e:
            revlbranch = self.lbranch
            
        try:
            revrbranch = self.rbranch.reverse
        except AttributeError as e:
            revrbranch = self.rbranch
            
        if self.op == "->":
            return Tree("->", revrbranch, revlbranch, rev=rev)     
        else:
            return Tree(self.op, revlbranch, revrbranch, rev=rev)
        
Path = Tree
        
class Node(object):
    def __init__(self, type, name=None):
        self.id = str(uuid.uuid4())
        self.type = type
        self.outgoing = collections.defaultdict(set) #This line needs converting
        self.incoming = collections.defaultdict(set) #This line needs converting
        self.name = name
        
    def __call__(self, query=None):
        if query is None:
            return set([self])
            
        if isinstance(query, str):
            tree = Tree(query)
        else:
            tree = query
            
        if tree.op == "atom":
            if tree.rev:
                return self.incoming.get(tree.lbranch, set())
            else:
                return self.outgoing.get(tree.lbranch, set())
        elif tree.op == "self":
            return set([self])
        elif tree.op == "->":
            match_all = set()
            match_left = self(tree.lbranch)

            for node in match_left:
                match_right = node(tree.rbranch)
                match_all |= match_right
                
            return match_all            
            #return set.union(set(),*[node(tree.rbranch) for node in self(tree.lbranch)])
        
        elif tree.op == "&":
            return self(tree.lbranch) & self(tree.rbranch)
        
        elif tree.op == "|":
            return self(tree.lbranch) | self(tree.rbranch)
        
        elif tree.op == "*":
            final_nodes = set([self])
            for node in self(tree.lbranch):
                final_nodes |= node(tree)
            return final_nodes
            #return reduce(set.union, [node(tree) for node in self(tree.lbranch)], set([self]))
            #return set.union(set([self]),*[node(tree) for node in self(tree.lbranch)])
        
        elif tree.op == "!":
            not_nodes = self(tree.lbranch)
            values = self.incoming.values() if tree.rev else self.outgoing.values()
            all_nodes = reduce(set.union, values, set())
            return all_nodes - not_nodes
        
    def __repr__(self):
        return "%s" % (self.name,)
                
class Graph(object):
    def __init__(self):
        self.nodes_by_id = dict() # This line needs converting
        
    def add_node(self, type, name=None):
        new_node = Node(type, name)
        self.nodes_by_id[new_node.id] = new_node
        return new_node
        
    def add_edge(self, start_node, end_node, type):
        start_node.outgoing[type].add(end_node)
        end_node.incoming[type].add(start_node)
        
    def __call__(self, id):
        return self.nodes_by_id[id]