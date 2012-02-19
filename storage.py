import collections
import uuid
# only reads need to be fast, so we can store on anything really, and just bang it into memory with sets and dicts

import redis

import graph


class PythonStorage(object):
    def __init__(self):
        self.id_dict = dict()

    def flush(self):
        pass
        
    def add_node(self, type, name):
        new_node = self.Node(type, name)
        self.id_dict[new_node.id] = new_node
        return new_node
    
    def add_edge(self, start_node, end_node, type):
        start_node.outgoing[type].add(end_node)
        end_node.incoming[type].add(start_node)
        
    def get_node(self, id):
        return self.id_dict[id]
    
    class Node(object):
        def __init__(self, type, name=None):
            self.id = str(uuid.uuid4())
            self.type = type
            self.outgoing = collections.defaultdict(set) 
            self.incoming = collections.defaultdict(set)
            self.name = name
        
        def get_outbound_nodes(self, type=None):
            if type is None:
                return reduce(set.union, self.outgoing.values(), set())
            return self.outgoing[type]
            
        def get_inbound_nodes(self, type=None):
            if type is None:
                return reduce(set.union, self.incoming.values(), set())
            return self.incoming[type]
            
        def __call__(self, query=None):
            return graph.traverse(self, query)
            
        def __repr__(self):
            return "%s" % (self.name,)
            

class RedisStorage(object):
    IDS_HASH = "ICING_NODE_HASH"

    def __init__(self, host='localhost', port=6379, db=0):
        self.rclient = redis.StrictRedis(host=host, port=port, db=db)
    
    def add_node(self, type, name):
        new_id = str(uuid.uuid4())
        new_node = self.Node(new_id, self)
        self.rclient.sadd(self.IDS_HASH, new_id)
        self.rclient.hset(new_id, "name", name)
        return new_node
        
    def add_edge(self, start_node, end_node, type):
        self.rclient.sadd("%s:outgoing:%s" % (start_node.id, type), end_node.id)
        self.rclient.sadd("%s:outgoing" % start_node.id, end_node.id)
        
        self.rclient.sadd("%s:incoming:%s" % (end_node.id, type), start_node.id)
        self.rclient.sadd("%s:incoming" % end_node.id, start_node.id)
    
    def get_node(self, node_id):
        return self.Node(node_id, self)
    
    def get_property(self, node_id, key):
        return self.rclient.hget(node_id, key)
    
    def get_outbound_nodes(self, node_id, type=None):
        if type is None:
            members = self.rclient.smembers("%s:outgoing" % node_id)
        else:
            members = self.rclient.smembers("%s:outgoing:%s" % (node_id, type))
        
        returnees = set()
        for member in members:
            returnees.add(self.Node(member, self))
            
        return returnees
        
    def get_inbound_nodes(self, node_id, type=None):
        if type is None:
            members = self.rclient.smembers("%s:incoming" % node_id)
        else:
            members = self.rclient.smembers("%s:incoming:%s" % (node_id, type))
            
        returnees = set()
        for member in members:
            returnees.add(self.Node(member, self))
            
        return returnees
    
    def flush(self):
        self.rclient.flushdb()
        
    class Node(object):
        def __init__(self, node_id, storage):
            self.id = node_id
            self.storage = storage
            
        def get_outbound_nodes(self, type=None):
            return self.storage.get_outbound_nodes(self.id, type)
            
        def get_inbound_nodes(self, type=None):
            return self.storage.get_inbound_nodes(self.id, type) 
            
        def __call__(self, query=None):
            return graph.traverse(self, query)
              
        def __getattr__(self, key):
            return self.storage.get_property(self.id, key)
        
        def __repr__(self):
            return "%s: %s: %s" % (self.name, uuid.UUID(self.id).int, self.id)

        def __eq__(x, y):
            return x.id == y.id
            
        def __hash__(self):
            return uuid.UUID(self.id).int