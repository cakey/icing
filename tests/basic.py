import unittest

import graph
from graph import Path
import storage

def mySetUp(self):
    self.g = graph.Graph(storage.PythonStorage)
    self.me = self.g.add_node("person", name="me")
    self.friend = self.g.add_node("person", name="friend")
    self.g.add_edge(self.me,self.friend,"friend")
    
    self.friend_of_friend = self.g.add_node("person", name="fof")
    self.g.add_edge(self.friend, self.friend_of_friend, "friend")
    self.eof = self.g.add_node("event", name="eof")
    self.g.add_edge(self.friend, self.eof, "attending")

    self.fofof = self.g.add_node("person", name="fofof")
    self.g.add_edge(self.friend_of_friend, self.fofof, "friend")
    
    self.mother = self.g.add_node("person", name="mother")
    self.g.add_edge(self.me, self.mother, "mother")
    
    self.friendlymother = self.g.add_node("person", name="friendymother")
    self.g.add_edge(self.me, self.friendlymother, "mother")
    self.g.add_edge(self.me, self.friendlymother, "friend")
    
    self.grandmother = self.g.add_node("person", name="grandmother")
    self.g.add_edge(self.mother, self.grandmother, "mother")
    
    
class TestAtomicConstructs(unittest.TestCase):
    def setUp(self):
        mySetUp(self)
    
    def test_(self):
        returnee = self.me()
        self.assertEqual(returnee, set([self.me]))
        
    def test_qu(self):
        returnee = self.me("")
        self.assertEqual(returnee, set([self.me]))
    
    def test_a(self):
        returnee = self.me("friend")
        self.assertEqual(returnee, set([self.friend, self.friendlymother]))
    
    def test_aa(self):
        returnee = self.me("friend->friend")
        self.assertEqual(returnee, set([self.friend_of_friend]))
        
    def test_aaa(self):
        returnee = self.me("friend->friend->friend")
        self.assertEqual(returnee, set([self.fofof]))
        
    def test_ab(self):
        returnee = self.me("friend->attending")
        self.assertEqual(returnee, set([self.eof]))
        
    def test_aORb(self):
        returnee = self.me("friend|mother")
        self.assertEqual(returnee, set([self.friend, self.mother, self.friendlymother]))
        
    def test_aANDb(self):
        returnee = self.me("friend&mother")
        self.assertEqual(returnee, set([self.friendlymother]))
        
    def test_aPLUS(self):
        returnee = self.me("mother+")
        self.assertEqual(returnee, set([self.mother, self.friendlymother, self.grandmother]))

    def test_aSTAR(self):
        returnee = self.me("mother*")
        self.assertEqual(returnee, set([self.me, self.mother, self.friendlymother, self.grandmother]))
    
    def test_NOTa(self):
        returnee = self.me("!friend")
        self.assertEqual(returnee, set([self.mother]))
    
    def test_a0(self):
        compare1 = self.me("friend0")
        compare2 = self.me()
        self.assertEqual(compare1, compare2)        
    
    def test_a1(self):
        compare1 = self.me("friend1")
        compare2 = self.me("friend")
        self.assertEqual(compare1, compare2)
        
    def test_a2(self):
        compare1 = self.me("friend2")
        compare2 = self.me("friend->friend")
        self.assertEqual(compare1, compare2)
      
    def test_a3(self):
        compare1 = self.me("friend3")
        compare2 = self.me("friend->friend->friend")
        self.assertEqual(compare1, compare2)
        
class TestParenthesis(unittest.TestCase):
    """
        Testing parenthesis by comparing them to what they would evaluate to,
        so that they are more isolated from screwups in the other atomic
        constructs
    """
    
    def setUp(self):
        mySetUp(self)
        
    def test_single(self):
        with_ = self.me("(friend)")
        without = self.me("friend")
        self.assertEqual(with_, without)
        
    def test_empty(self):
        with_ = self.me("(())")
        without = self.me()
        self.assertEqual(with_, without)        
       
    def test_single_prec(self):
        with_ = self.me("friend|(mother->mother)")
        without = self.me("friend") | self.me("mother->mother")
        self.assertEqual(with_, without)
        
    def test_single_prec2(self):
        with_ = self.me("(friend->mother)|mother")
        without = self.me("friend->mother") | self.me("mother")
        self.assertEqual(with_, without)

    def test_not(self):
        compare1 = self.me("(!(!(friend)))")
        compare2 = self.me("friend")
        self.assertEqual(compare1, compare2) 
        
class TestComposite(unittest.TestCase):

    def setUp(self):
        mySetUp(self)
        
    def test_NOTNOT(self):
        compare1 = self.me("!!friend")
        compare2 = self.me("friend")
        self.assertEqual(compare1, compare2)        

class TestById(unittest.TestCase):
    def setUp(self):
        mySetUp(self)
        
    def test_single(self):
        orignode = self.g(self.me.id)
        self.assertEqual(orignode, self.me)

class TestQuestion(unittest.TestCase):
    def setUp(self):
        mySetUp(self)
        
    def test_q_TRUE(self):
        Mother = Path("mother")
        self.assertTrue(Mother.test(self.me, self.mother))
        #self.assertTrue(self.mother in Mother(self.me))
        
    def test_q_FALSE(self):
        Mother = Path("mother")
        self.assertFalse(Mother.test(self.me, self.friend))
        
class TestReverse(unittest.TestCase):
    def setUp(self):
        mySetUp(self)
        
    def test_rev_a(self):
        Mother = Path("mother")
        MothersChild = Mother.reverse
        self.assertEqual(MothersChild(self.mother), set([self.me]))
        
    def test_double_rev(self):
        Friendstar = Path("friend+")
        
        Friendstar2 = Friendstar.reverse.reverse
        self.assertEqual(Friendstar(self.me), Friendstar2(self.me))
        
    def test_rev_aa(self):
        Doublef = Path("friend->friend")
        
        self.assertEqual(Doublef.reverse(self.friend_of_friend), set([self.me]))

        
        
class TestChain(unittest.TestCase):
    def setUp(self):
        mySetUp(self)    
    
    def test_c_callable(self):
        Mother = Path("mother")
        mothers1 = Mother(self.me)
        mothers2 = self.me("mother")
        
        self.assertEqual(mothers1, mothers2)

    def test_c_aa(self):
        Mother = Path("mother")
        Grandmother = Mother(Mother)
        grandmothers1 = Grandmother(self.me)
        grandmothers2 = self.me("mother->mother")
        
        self.assertEqual(grandmothers1, grandmothers2)
        
    def test_c_aORb(self):
        Friend = Path("friend")
        Mother = Path("mother")
        FriendOrMother = Friend | Mother
        returnee1 = self.me("friend|mother")
        returnee2 = FriendOrMother(self.me)
        self.assertEqual(returnee1, returnee2)
        
        returnee3 = (Friend | Mother)(self.me)
        self.assertEqual(returnee1, returnee3)
        
    def test_c_aANDb(self):
        Friend = Path("friend")
        Mother = Path("mother")
        FriendAndMother = Friend & Mother
        returnee1 = self.me("friend&mother")
        returnee2 = FriendAndMother(self.me)
        self.assertEqual(returnee1, returnee2)
        
        returnee3 = (Friend & Mother)(self.me)
        self.assertEqual(returnee1, returnee3)

    def test_c_aPLUS(self):
        Mother = Path("mother")
        returnee1 = self.me("mother+")
        returnee2 = Mother['+'](self.me)
        self.assertEqual(returnee1, returnee2)

    def test_c_aSTAR(self):
        Mother = Path("mother")
        returnee1 = self.me("mother*")
        returnee2 = Mother['*'](self.me)
        self.assertEqual(returnee1, returnee2)
      
    def test_c_a0(self):
        Friend = Path("friend")
        compare1 = self.me("friend0")
        compare2 = Friend[0](self.me)
        self.assertEqual(compare1, compare2)        
    
    def test_c_a1(self):
        Friend = Path("friend")
        compare1 = self.me("friend1")
        compare2 = Friend[1](self.me)
        self.assertEqual(compare1, compare2)
        
    def test_c_a2(self):
        Friend = Path("friend")
        bench = self.me("friend2")
        new = Friend[2](self.me)
        self.assertEqual(bench, new)
        
if __name__ == '__main__':
    unittest.main()