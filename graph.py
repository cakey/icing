# TODO
# d |& operator
# d */+
# d num
# d paranthesis
# d *args (tree based on how many args are passed)
# d chaining
# d pull out traverse logic into RelationshipQuery class to it can be
# d     'precompiled' and chained
# d test coverage
#   hamcrest
# d want to query in reverse
#   unit test bad input
#   optimise applying querys to sets
#   optional type safety
# d abstract out dicts/set to let them be backed by anything
# d relationships with more than one root (mutual friends)
# d back the dicts/sets by redis
#   consider the best way to persist dicts/sets
# d 'are these two nodes linked by this path'
#   can apply queries to sets (collection extends set, is callable)
#       do we return as dicts or sets?
#   limit on duration
# d track route
#   indexing
#   get/set properties
#   querying based on property
#   neo4j wrapper! (lol) (write a wrapper for each layer?)
#   allow traverser etc to default to storage implementation if exposed...

import collections
import string
import uuid

from storage import PythonStorage

def query_parser(query):
    if not query:
        return Tree()
    
    if query.startswith("!"):
        return Tree("!", query_parser(query[1:]))
        
    if query.startswith("(") and query.endswith(")"):
        return query_parser(query[1:-1])
        
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
            op = "->" if before.endswith("->") else before[-1]
            lbranch = before[0:-2] if before.endswith("->") else before[0:-1]
        if after:
            tree = Tree()
            tree.op = "->" if after.startswith("->") else after[0]
            tree.lbranch = during
            tree.rbranch = after[2:] if after.startswith("->") else after[1:]
            rbranch = tree
            if not before:
                op, lbranch, rbranch = tree.op, tree.lbranch, tree.rbranch
        else:
            rbranch=during
            
        return Tree(op, lbranch, rbranch)
    
    # the order here defines precendence
    for op in ["->", "&", "|", "-"]:
        if op in query:
            branches = query.split(op)
            lbranch = query_parser(branches[0])
            rbranch = query_parser(op.join(branches[1:]))
            return Tree(op, lbranch, rbranch)
    for op in ('*','+'):
        if query.endswith(op):
            return Tree(op, query_parser(query[0:-1]))
        
    # causes issues with recursion:
    #if query.endswith("+"):
    #    self.op = "->"
    #    tree = Tree(query[0:-1])
    #    self.lbranch = tree
    #    self.rbranch = Tree('*', tree)
    #    return
    
    if query[-1] in string.digits:
        num = int(query[-1])
        if num == 0:
            return Tree()
        elif num == 1:
            return query_parser(query[0:-1])
        else: 
            tree = query_parser(query[0:-1])
            return Tree("->", tree, query_parser(query[0:-1] + str(num-1)))

    return Tree("atom", query)

class Tree(object):
    def __init__(self, *args, **kwargs):
        self._rev = kwargs.get("_rev", False)
        self.op = None
        self.lbranch = None
        self.rbranch = None
        
        props = [key for key in kwargs if key != '_rev']
        # if there is one property to match against, 
        # then set the key to lbranch, and the value to rbranch
        if len(props) == 1:
            self.op = 'prop'
            self.lbranch = props[0]
            self.rbranch = kwargs[props[0]]
            return
        # if there are multiple properties, 
        # then create a tree for each property then and them together.
        elif len(props) >= 1:
            self.op = '&'
            propdict = {props[0]:kwargs[props[0]]}
            self.lbranch = Tree(**propdict)
            del kwargs[props[0]]
            self.rbranch = Tree(**kwargs)
            return 
        
        if len(args) == 0:
            self.op = 'self'
            return
        
        # standard case of being called with a query string
        if len(args) == 1:
            query = args[0]
        
        # Constructing a tree from 1 arg ops
        if len(args) == 2:
        
            op = args[0]
            tree = args[1]
            if op == "!":
                # demorgans
                if tree.op == "&":
                    self.op = "|"
                    self.lbranch = Tree("!", tree.lbranch)
                    self.rbranch = Tree("!", tree.rbranch)
                elif tree.op == "|":
                    self.op == "&"
                    self.lbranch = Tree("!", tree.lbranch)
                    self.rbranch = Tree("!", tree.rbranch)
                elif tree.op == "!":
                    self.op = tree.lbranch.op
                    self.lbranch = tree.lbranch.lbranch
                    self.rbranch = tree.lbranch.rbranch
                elif tree.op == "->":
                    newtree = Tree("|", Tree("->", tree.lbranch, Tree("!", tree.rbranch)),
                                        Tree("|", Tree("->", Tree("!", tree.lbranch),  tree.rbranch),
                                                Tree("->", Tree("!", tree.lbranch), Tree("!", tree.rbranch))))               
                    self.op, self.lbranch, self.rbranch = newtree.op, newtree.lbranch, newtree.rbranch
                else:
                    self.op = "!"
                    self.lbranch = tree
            else:
                self.op = op
                self.lbranch = tree
            return
        
        # constructing a tree from 2 arg ops
        if len(args) == 3:
            self.op = args[0]
            self.lbranch = args[1]
            self.rbranch = args[2]
            return 
        
        # else we have a query
        
        tree = query_parser(query)
        self.op, self.lbranch, self.rbranch = tree.op, tree.lbranch, tree.rbranch
            
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
        
    def __sub__(self, other):
        return Tree("-", self, other)
        
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
    
    def if_has(self, *args, **kwargs):
        if len(args) == 0 and len(kwargs) > 0:
            return Tree("if", self, Tree(**kwargs))
        else:
            return Tree("if", self, args[0])
    
    def test(self, first, second):
        # TODO: come at from both outgoing,
        #    or you might as well just use 'in' yourself.
        return second in self(first)
    
    @property    
    def reverse(self):
        _rev = not self._rev
        try:
            revlbranch = self.lbranch.reverse
        except AttributeError as e:
            revlbranch = self.lbranch
            
        try:
            revrbranch = self.rbranch.reverse
        except AttributeError as e:
            revrbranch = self.rbranch
            
        if self.op == "->":
            return Tree("->", revrbranch, revlbranch, _rev=_rev)     
        else:
            return Tree(self.op, revlbranch, revrbranch, _rev=_rev)
        
Path = Tree

class MultiPath(object):
    def __init__(self, *paths):
        self.paths = paths
      
    def __call__(self, *nodes):
        results = []
        for path, node in zip(self.paths, nodes):
            results.append(path(node))
        
        matching_nodes = {}
        for node in results[0]:
            if all(node in result for result in results):
                matching_nodes[node] = [result[node] for result in results]
                
        return matching_nodes

def traverse(node, query=None, ancestors=None):
    # d initialise if no ancestors
    #   append self to ancestors
    #   pass ancestors through traverse
    #   if self in ancestors - short circuit
    
    if ancestors is None:
        ancestors = set()
        
    if query is None:
        return {node:[]}

        
    if isinstance(query, str):
        tree = Tree(query)
    else:
        tree = query
    
    def atom(node, tree):
        type = tree.lbranch
        if tree._rev:
            return {node:[(type,node)] for node in node.get_inbound_nodes(type)[type]}
        else:
            return {node:[(type,node)] for node in node.get_outbound_nodes(type)[type]}
     
    def identity(node, tree):
        return {node:[]}

    def concatenation(node, tree):
        match_all = collections.defaultdict(list)
        match_left = traverse(node,tree.lbranch)

        for lnode, lpath in match_left.iteritems():
            match_right = traverse(lnode,tree.rbranch)
            for rnode,rpath in match_right.iteritems():
                match_all[rnode] = lpath+rpath
            
        return match_all            
    
    def difference(node, tree):
        left = traverse(node, tree.lbranch)
        right = traverse(node, tree.rbranch)
        returnee = {}
        for key, path in left.iteritems():
            if key not in right:
                returnee[key] = path
        return returnee
    
    def intersection(node, tree):
        left = traverse(node, tree.lbranch)
        right = traverse(node, tree.rbranch)
        returnee = {}
        for key, path in left.iteritems():
            if key in right:
                returnee[key] = path
        return returnee
    
    def union(node, tree):
        left = traverse(node, tree.lbranch)
        right = traverse(node, tree.rbranch)
        left.update(right)
        return left
    
    def one_or_more(node, tree):
        if node in ancestors:
            return {}
        ancestors.add(node)

        match_left = traverse(node,tree.lbranch)

        final_nodes = {}
        
        tree.op = "*"
        for lnode, lpath in match_left.iteritems():
            for rnode, rpath in traverse(lnode, tree, ancestors).iteritems():
                final_nodes[rnode] = lpath+rpath
        return final_nodes
    
    def zero_or_more(node, tree):
        final_nodes = {node:[]}
        if node in ancestors:
            return {}
        ancestors.add(node)
        for lnode, lpath in traverse(node, tree.lbranch, ancestors).iteritems():
            for rnode, rpath in traverse(lnode, tree, ancestors).iteritems():
                final_nodes[rnode] = lpath+rpath
        return final_nodes
    
    def complement(node, tree):
        # set of nodes with paths
        not_nodes = traverse(node, tree.lbranch)
        
        # dict... type:[nodes]
        all_nodes_dict = node.get_inbound_nodes() if tree._rev else node.get_outbound_nodes()
        
        actual_nodes = dict()
        
        # for each node edge, only keep it if it wasnt in the path
        for type, nodes in all_nodes_dict.iteritems():
            for node in nodes:
                if node not in not_nodes:
                    actual_nodes[node] = [(type,node)]
                    
        return actual_nodes
    
    def conditional(node, tree):
        candidates = traverse(node, tree.lbranch)
        
        matching_nodes = {}
        for candidate, path in candidates.iteritems():
            if traverse(candidate, tree.rbranch):
                matching_nodes[candidate] = path
              
        return matching_nodes
    
    def property(node, tree):
        if getattr(node, tree.lbranch) == tree.rbranch:
            return {node: []}
        else:
            return dict()
    
    def default(node, tree):
        raise ValueError("Tree operation not supported: {%s}." % tree.op)
        
    interpreter = {'atom':atom,
                   'self':identity,
                   '->':concatenation,
                   '-':difference,
                   '&':intersection,
                   '|':union,
                   '+':one_or_more,
                   '*':zero_or_more,
                   '!':complement,
                   'if':conditional,
                   'prop':property}
    
    return interpreter.get(tree.op, default)(node, tree)
        
class Node(object):
    def __init__(self, node_id, storage):
        self.id = node_id
        self.storage = storage
        
    def get_outbound_nodes(self, type=None):
        return self.storage.get_outbound_nodes(self.id, type)
        
    def get_inbound_nodes(self, type=None):
        return self.storage.get_inbound_nodes(self.id, type) 
        
    def __call__(self, query=None):
        return  traverse(self, query)
          
    def __getattr__(self, key):
        return self.storage.get_property(self.id, key)

    def __setattr__(self, key, value):
        if key in ['id', 'storage']: # hack :(
            object.__setattr__(self, key, value)
        else:
            self.storage.set_property(self.id, key, value)
        
    def __repr__(self):
        #return "%s: %s: %s" % (self.name, uuid.UUID(self.id).int, self.id)
        return self.name
    def __eq__(x, y):
        return x.id == y.id
        
    def __hash__(self):
        return uuid.UUID(self.id).int
            
class Graph(object):
    def __init__(self, storage=None):
        if storage is None:
            storage = PythonStorage
        self.storage = storage()
        
    def add_node(self, type, name=None):
        
        return self.storage.add_node(type, name)
        
    def add_edge(self, start_node, end_node, type):
        self.storage.add_edge(start_node, end_node, type)
        
    def __call__(self, node_id):
        return self.storage.get_node(node_id)
        
    def flush(self):
       self.storage.flush() 