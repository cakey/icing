import unittest

import nose
from nose.plugins.skip import SkipTest

from .. import graph
from ..graph import Path, MultiPath
from .. import storage as Storage

class RedisBack(object):
    storage = Storage.RedisStorage
    #storage = storage.PythonStorage
    
class PythonBack(object):
    storage = Storage.PythonStorage

def mySetUp(self):
    self.storage().flush()
    self.g = graph.Graph(self.storage)
    self.me = self.g.add_node("person", name="me")
    self.friend = self.g.add_node("person", name="friend")
    self.g.add_edge(self.me,self.friend,"friend")
    
    self.friend_of_friend = self.g.add_node("person", name="fof")
    self.g.add_edge(self.friend, self.friend_of_friend, "friend")
    self.g.add_edge(self.friend_of_friend, self.friend, "friend")
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
    
class AtomicConstructs(object):
    def setUp(self):
        mySetUp(self)
    
    def test_(self):
        returnee = self.me()
        self.assertEqual(set(returnee.keys()), set([self.me]))
        
    def test_qu(self):
        returnee = self.me("")
        self.assertEqual(set(returnee.keys()), set([self.me]))
    
    def test_a(self):
        returnee = self.me("friend")
        self.assertEqual(set(returnee.keys()), set([self.friend, self.friendlymother]))
    
    def test_aa(self):
        returnee = self.me("friend->friend")
        self.assertEqual(set(returnee.keys()), set([self.friend_of_friend]))
        
    def test_aaa(self):
        returnee = self.me("friend->friend->friend")
        self.assertEqual(set(returnee.keys()), set([self.fofof, self.friend])) 
        # issue here that we end up doubling back on nodes weve seen!
        # you would solve this with an if
        
    def test_ab(self):
        returnee = self.me("friend->attending")
        self.assertEqual(set(returnee.keys()), set([self.eof]))
        
    def test_aORb(self):
        returnee = self.me("friend|mother")
        self.assertEqual(set(returnee.keys()), set([self.friend, self.mother, self.friendlymother]))
        
    def test_aANDb(self):
        returnee = self.me("friend&mother")
        self.assertEqual(set(returnee.keys()), set([self.friendlymother]))
        
    def test_aPLUS(self):
        returnee = self.me("mother+")
        self.assertEqual(set(returnee.keys()), set([self.mother, self.friendlymother, self.grandmother]))

    def test_aSTAR(self):
        returnee = self.me("mother*")
        self.assertEqual(set(returnee.keys()), set([self.me, self.mother, self.friendlymother, self.grandmother]))
    
    def test_aBUTNOTb(self):
        returnee = self.me("friend-mother")
        self.assertEqual(set(returnee.keys()), set([self.friend]))
    
    def test_NOTa(self):
        returnee = self.me("!friend")
        self.assertEqual(set(returnee.keys()), set([self.mother]))
    
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

class PyTestAtomicConstructs(AtomicConstructs, unittest.TestCase, PythonBack):    pass
class ReTestAtomicConstructs(AtomicConstructs, unittest.TestCase, RedisBack):    pass
    
class Parenthesis(object):
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
        without = self.me("friend")
        without.update(self.me("mother->mother"))
        self.assertEqual(with_, without)
        
    def test_single_prec2(self):
        with_ = self.me("(friend->mother)|mother")
        without = self.me("friend->mother")
        without.update(self.me("mother"))
        self.assertEqual(with_, without)

    def test_not(self):
        #raise SkipTest()

        compare1 = self.me("(!(!(friend)))")
        compare2 = self.me("friend")
        self.assertEqual(compare1, compare2) 

class PyTestParenthesis(Parenthesis, unittest.TestCase, PythonBack):    pass
class ReTestParenthesis(Parenthesis, unittest.TestCase, RedisBack):    pass
        
class Composite(object):

    def setUp(self):
        mySetUp(self)
        
    def test_NOTNOT(self):
        #raise SkipTest()

        compare1 = self.me("!!friend")
        compare2 = self.me("friend")
        self.assertEqual(compare1, compare2)       

    def test_NOTab(self):
        compare1 = self.me("!(friend->friend)")
        self.assertEqual(set(compare1.keys()), set([self.grandmother, self.eof]))

    def test_recursion_when_STAR_applied_to_inner_path(self):
        """ Test that when we apply * to a smaller path, where the * would recurse infinitely, that it stops
            correctly when it reaches a node it's already seen, but its allowed to see the
            ancestor node within the inner path!
        """
        Friendstar = Path("friend*")
        Friendstar2 = Path("(friend|lol)*")
        
        rec_friends = Friendstar(self.me)
        rec_friends2 = Friendstar2(self.me)
        
        self.assertEqual(set(rec_friends.keys()), set(rec_friends2.keys()))
        
    def test_recursion_with_PLUS(self):
        """ Test that PLUS doesn't include itself on a recursive path! """
        # This fails because we convert + to (->*)
        Friendplus = Path("friend+")
        
        rec_friends = Friendplus(self.friend_of_friend)
        
        self.assertEqual(set(rec_friends.keys()), set([self.friend, self.fofof]))

        
class PyTestComposite(Composite, unittest.TestCase, PythonBack):
    pass

class ReTestComposite(Composite, unittest.TestCase, RedisBack):
    pass
        
class ById(object):
    def setUp(self):
        mySetUp(self)
        
    def test_single(self):
        orignode = self.g(self.me.id)
        self.assertEqual(orignode, self.me)

class PyTestById(ById, unittest.TestCase, PythonBack):
    pass

class ReTestById(ById, unittest.TestCase, RedisBack):
    pass        
        
class Question(object):
    def setUp(self):
        mySetUp(self)
        
    def test_q_TRUE(self):
        Mother = Path("mother")
        self.assertTrue(Mother.test(self.me, self.mother))
        #self.assertTrue(self.mother in Mother(self.me))
        
    def test_q_FALSE(self):
        Mother = Path("mother")
        self.assertFalse(Mother.test(self.me, self.friend))

class PyQuestion(Question, unittest.TestCase, PythonBack):
    pass

class ReQuestion(Question, unittest.TestCase, RedisBack):
    pass     
        
class Reverse(object):
    def setUp(self):
        mySetUp(self)
        
    def test_rev_a(self):
        Mother = Path("mother")
        MothersChild = Mother.reverse
        self.assertEqual(set(MothersChild(self.mother).keys()), set([self.me]))
        
    def test_double_rev(self):
        Friendstar = Path("friend*")
        
        Friendstar2 = Friendstar.reverse.reverse
        self.assertEqual(Friendstar(self.me), Friendstar2(self.me))
        
    def test_rev_aa(self):
        Doublef = Path("friend->friend")
        
        self.assertEqual(set(Doublef.reverse(self.friend_of_friend).keys()), set([self.me, self.friend_of_friend]))

class PyReverse(Reverse, unittest.TestCase, PythonBack):
    pass

class ReReverse(Reverse, unittest.TestCase, RedisBack):
    pass     
        
class Chain(object):
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

    def test_c_aBUTNOTb(self):
        Friend = Path("friend")
        Mother = Path("mother")
        FriendButNotMother = Friend - Mother
        returnee1 = self.me("friend-mother")
        returnee2 = FriendButNotMother(self.me)
        self.assertEqual(returnee1, returnee2)
        
        returnee3 = (Friend - Mother)(self.me)
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

class PyChain(Chain, unittest.TestCase, PythonBack):
    pass

class ReChain(Chain, unittest.TestCase, RedisBack):
    pass  

class Track(object):
    def setUp(self):
        mySetUp(self)
        
    def test_tr_aa(self):
        Friend = Path("friend")
        Fof = Friend(Friend)
        
        path = Fof(self.me)
        
        self.assertEqual(path[self.friend_of_friend], [("friend", self.friend),("friend", self.friend_of_friend)])
        
class PyTrack(Track, unittest.TestCase, PythonBack):    pass
class ReTrack(Track, unittest.TestCase, RedisBack):    pass

class MultiPathTest(object):
    def setUp(self):
        mySetUp(self)
        
    def test_mp_multipath1(self):
        Friend = Path("friend")
        MutualFriend = MultiPath(Friend, Friend)
        mutual_friends1 = MutualFriend(self.me, self.friend_of_friend)
        mutual_friends2 = set(Friend(self.me).keys()) & set(Friend(self.friend_of_friend).keys())
        
        self.assertEqual(set(mutual_friends1.keys()), mutual_friends2)
        self.assertEqual(set(mutual_friends1.keys()), set([self.friend]))
        
    
class PyTestMultiPath(MultiPathTest, unittest.TestCase, PythonBack):    pass
class ReTestMultiPath(MultiPathTest, unittest.TestCase, RedisBack):    pass
    
#testclasses = {TestAtomicConstructs, TestParenthesis, TestComposite, TestById, TestById, TestQuestion, TestReverse, TestChain}
#backs = {RedisBack, PythonBack}
#allsuites = []
#for back in backs:
#    for tc in testclasses:
#        class myclass(tc, back, unittest.TestCase):
#            pass
#        suite = unittest.TestLoader().loadTestsFromTestCase(tc())
#        allsuites.append(suite)
#allthesuites = unittest.TestSuite(allsuites)        
if __name__ == '__main__':
    unittest.main()