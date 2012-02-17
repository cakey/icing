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
# can apply queries to sets
# somehow optimise the above
# unit test bad input

import collections
import uuid

class node(object):
    def __init__(self, type, name=None):
        self.id = str(uuid.uuid4())
        self.type = type
        self.edges = collections.defaultdict(set)
        self.name = name
        
    def __call__(self, query):
        if not isinstance(
        first = query.split("->")[0]
        rest = "->".join(query.split("->")[1:])
        
        ands = first.split("&")
        next_nodes = set()
        for i, and_ in enumerate(ands):
            ors = and_.split("|")
            _next_nodes = set()
            for or_ in ors:
                __next_nodes = set()
                if or_[-1] == "*":
                    __next_nodes.add(self)                    
                    for node in self.edges.get(or_[0:-1], set()):
                        __next_nodes |= node(or_)
                        
                elif or_[-1] == "+":
                    for node in self.edges.get(or_[0:-1], set()):
                        __next_nodes |= node(or_[0:-1]+"*")
                else:
                    __next_nodes = self.edges.get(or_, set())
                _next_nodes |= __next_nodes
            if i == 0:
                next_nodes = _next_nodes
            else:
                next_nodes &= _next_nodes

            
        if rest == "":
            return next_nodes
        else:
            final_nodes = set()
            for node in next_nodes:
                final_nodes |= node(rest)
            return final_nodes
            
    def __repr__(self):
        return "%s" % (self.name,)

class graph(object):
    def __init__(self):
        self.nodes_by_id = dict()
        
    def add_node(self, type, name=None):
        new_node = node(type, name)
        self.nodes_by_id[new_node.id] = new_node
        return new_node
        
    def add_edge(self, start_node, end_node, type):
        start_node.edges[type].add(end_node)