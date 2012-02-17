# TODO
# |& operator
# */+/num
# paranthesis
# optional type safety
# chaining
# want to query in reverse
# hamcrest
# limit on duration
# pull out traverse logic into RelationshipQuery class to it can be
#   'precompiled' and chained
# can apply queries to sets (collection extends set, is callable)
# somehow optimise the above
# unit test bad input

import collections
import uuid

class Tree(object):
    def __init__(self,query, cop=None, cbranches=None):
        self.op = None
        self.lbranch = None
        self.rbranch = None
        
        #"c->a|(a->b)|b"
        
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
                tree = Tree('')
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
            startree = Tree('')
            startree.op = "*"
            startree.lbranch = tree
            self.rbranch = startree
            return
        
        self.op = "atom"
        self.lbranch = query
            
    def __repr__(self):
        return "%s(%s,%s)" % (self.op, self.lbranch, self.rbranch)
        
class Node(object):
    def __init__(self, type, name=None):
        self.id = str(uuid.uuid4())
        self.type = type
        self.edges = collections.defaultdict(set)
        self.name = name
        
    def __call__(self, query):
        if isinstance(query, str):
            tree = Tree(query)
        else:
            tree = query
            
        if tree.op == "atom":
            return self.edges.get(tree.lbranch, set())
            
        elif tree.op == "->":
            final_nodes = set()
            next_nodes = self(tree.lbranch)

            for node in next_nodes:
                final_nodes |= node(tree.rbranch)
                
            return final_nodes            
            #return set.union(*[node(tree.rbranch) for node in self(tree.lbranch)])
        
        elif tree.op == "&":
            return self(tree.lbranch) & self(tree.rbranch)
        
        elif tree.op == "|":
            return self(tree.lbranch) | self(tree.rbranch)
        
        elif tree.op == "*":
            final_nodes = set([self])
            for node in self(tree.lbranch):
                final_nodes |= node(tree)
            return final_nodes
            
        elif tree.op == "+":
            final_nodes = set()
            for node in self(tree.lbranch):
                final_nodes |= node(tree)
            return final_nodes
            
    def __repr__(self):
        return "%s" % (self.name,)
                
class Graph(object):
    def __init__(self):
        self.nodes_by_id = dict()
        
    def add_node(self, type, name=None):
        new_node = Node(type, name)
        self.nodes_by_id[new_node.id] = new_node
        return new_node
        
    def add_edge(self, start_node, end_node, type):
        start_node.edges[type].add(end_node)