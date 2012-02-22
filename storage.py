import collections
import uuid
# only reads need to be fast, so we can store on anything really, and just bang it into memory with sets and dicts

import redis

import graph


class PythonStorage(object):
    def __init__(self):
        self.flush()
        
    def flush(self):
        self.id_dict = dict()
        self.propertydict = collections.defaultdict(dict)
        
        self.edges = {'incoming':collections.defaultdict(lambda:collections.defaultdict(set)),
                      'outgoing':collections.defaultdict(lambda:collections.defaultdict(set))}

        
    def add_node(self, type, name):
        new_id = str(uuid.uuid4())
        new_node = graph.Node(new_id, self)
        self.id_dict[new_node.id] = new_node
        self.propertydict[new_node.id]["name"] = name
        return new_node
    
    def get_property(self, id, key):
        return self.propertydict[id].get(key, None)
    
    def add_edge(self, start_node, end_node, type):
        self.edges['outgoing'][start_node.id][type].add(end_node.id)
        self.edges['incoming'][end_node.id][type].add(start_node.id)
    
    def _get_nodes(self, id, direction, type=None):
        if type is None:
            returnees = collections.defaultdict(set)
            for _type, _nodes in self.edges[direction][id].iteritems():
                for _node in _nodes:
                    returnees[_type].add(graph.Node(_node, self))
            return returnees
        else:
            returnees = collections.defaultdict(set)
            node_ids = self.edges[direction][id][type]
            for node_id in node_ids:
                returnees[type].add(graph.Node(node_id, self))
            return returnees
        
        
    def get_outbound_nodes(self, node_id, type=None):
        return self._get_nodes(node_id, "outgoing", type)
        
    def get_inbound_nodes(self, node_id, type=None):
        return self._get_nodes(node_id, "incoming", type)
        
    def get_node(self, id):
        return self.id_dict[id]
        

class RedisStorage(object):
    IDS_HASH = "ICING_NODE_HASH"

    def __init__(self, host='localhost', port=6379, db=0):
        self.rclient = redis.StrictRedis(host=host, port=port, db=db)
    
    def add_node(self, type, name):
        new_id = str(uuid.uuid4())
        new_node = graph.Node(new_id, self)
        self.rclient.sadd(self.IDS_HASH, new_id)
        self.rclient.hset(new_id, "name", name)
        return new_node
        
    def add_edge(self, start_node, end_node, type):
        self.rclient.sadd("%s:outgoing:%s" % (start_node.id, type), end_node.id)
        self.rclient.sadd("%s:outgoing" % start_node.id, type)
        
        self.rclient.sadd("%s:incoming:%s" % (end_node.id, type), start_node.id)
        self.rclient.sadd("%s:incoming" % end_node.id, type)
    
    def get_node(self, node_id):
        return graph.Node(node_id, self)
    
    def get_property(self, node_id, key):
        return self.rclient.hget(node_id, key)
    
    def _get_nodes(self, node_id, direction, type=None):
        returnees = collections.defaultdict(set)       
        if type is None:
            types   = self.rclient.smembers("%s:%s" % (node_id,direction))
            for _type in types:
                members = self.rclient.smembers("%s:%s:%s" % (node_id, direction, _type))
                for member in members:
                    returnees[_type].add(graph.Node(member, self))
        else:
            members = self.rclient.smembers("%s:%s:%s" % (node_id, direction, type))
            for member in members:
                returnees[type].add(graph.Node(member, self))
            
        return returnees
    
    def get_outbound_nodes(self, node_id, type=None):
        return self._get_nodes(node_id, "outgoing", type)
        
    def get_inbound_nodes(self, node_id, type=None):
        return self._get_nodes(node_id, "incoming", type)
    
    def flush(self):
        self.rclient.flushdb()