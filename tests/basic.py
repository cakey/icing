import unittest

import graph

def mySetUp(self):
    self.g = graph.Graph()
    self.original = self.g.add_node("person", name="original")
    self.friend = self.g.add_node("person", name="friend")
    self.g.add_edge(self.original,self.friend,"friend")
    
    self.friend_of_friend = self.g.add_node("person", name="fof")
    self.g.add_edge(self.friend, self.friend_of_friend, "friend")
    self.eof = self.g.add_node("event", name="eof")
    self.g.add_edge(self.friend, self.eof, "attending")

    self.fofof = self.g.add_node("person", name="fofof")
    self.g.add_edge(self.friend_of_friend, self.fofof, "friend")
    
    self.mother = self.g.add_node("person", name="mother")
    self.g.add_edge(self.original, self.mother, "mother")
    
    self.friendlymother = self.g.add_node("person", name="friendymother")
    self.g.add_edge(self.original, self.friendlymother, "mother")
    self.g.add_edge(self.original, self.friendlymother, "friend")
    
    self.grandmother = self.g.add_node("person", name="grandmother")
    self.g.add_edge(self.mother, self.grandmother, "mother")
    
    
class TestAtomicConstructs(unittest.TestCase):
    def setUp(self):
        mySetUp(self)
        
    def test_a(self):
        returnee = self.original("friend")
        self.assertEqual(returnee, set([self.friend, self.friendlymother]))
    
    def test_aa(self):
        returnee = self.original("friend->friend")
        self.assertEqual(returnee, set([self.friend_of_friend]))
        
    def test_aaa(self):
        returnee = self.original("friend->friend->friend")
        self.assertEqual(returnee, set([self.fofof]))
        
    def test_ab(self):
        returnee = self.original("friend->attending")
        self.assertEqual(returnee, set([self.eof]))
        
    def test_aORb(self):
        returnee = self.original("friend|mother")
        self.assertEqual(returnee, set([self.friend, self.mother, self.friendlymother]))
        
    def test_aANDb(self):
        returnee = self.original("friend&mother")
        self.assertEqual(returnee, set([self.friendlymother]))
        
    def test_aPLUS(self):
        returnee = self.original("mother+")
        self.assertEqual(returnee, set([self.mother, self.friendlymother, self.grandmother]))

    def test_aSTAR(self):
        returnee = self.original("mother*")
        self.assertEqual(returnee, set([self.original, self.mother, self.friendlymother, self.grandmother]))
    
class TestParenthesis(unittest.TestCase):
    """
        Testing parenthesis by comparing them to what they would evaluate to,
        so that they are more isolated from screwups in the other atomic
        constructs
    """
    
    def setUp(self):
        mySetUp(self)
        
    def test_single(self):
        with_ = self.original("(friend)")
        without = self.original("friend")
        self.assertEqual(with_, without)
       
    def test_single_prec(self):
        with_ = self.original("friend|(mother->mother)")
        without = self.original("friend") | self.original("mother->mother")
        self.assertEqual(with_, without)
        
    def test_single_prec2(self):
        with_ = self.original("(friend->mother)|mother")
        without = self.original("friend->mother") | self.original("mother")
        self.assertEqual(with_, without)
        
if __name__ == '__main__':
    unittest.main()