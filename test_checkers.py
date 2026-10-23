import unittest
from types import SimpleNamespace
from checkers import CheckersRules, CheckersState, CheckersApp, NAMES, PLAYABLE, search_checkers

def sq(name): return NAMES.index(name)

def position(white,black,kings_white=(),kings_black=(),turn=1,active=-1):
    b=[0]*64
    for names,value in ((white,1),(black,2),(kings_white,-1),(kings_black,-2)):
        for name in names:
            i=sq(name)
            if i not in PLAYABLE: raise ValueError(name)
            b[i]=value
    return CheckersState(tuple(b),turn,active)

def move(src,dst,jump=False): return (sq(src),sq(dst),'J' if jump else 'P')

class CheckersTests(unittest.TestCase):
    def test_opening(self):
        r=CheckersRules(); s=r.initial()
        self.assertEqual((s.board.count(1),s.board.count(2)),(12,12))
        self.assertEqual(s.turn,2)
        self.assertEqual(len(r.actions(s)),7)
        self.assertTrue(all(i in PLAYABLE for i,v in enumerate(s.board) if v))
        self.assertTrue(all(a[2]=='P' and a[1]>a[0] for a in r.actions(s)))
        t=r.play(s,r.actions(s)[0]); self.assertEqual(t.turn,1)

    def test_men_move_forward_and_do_not_wrap(self):
        r=CheckersRules(); s=position(['a3'],['h8'])
        self.assertEqual(r.actions(s),[move('a3','b4')])
        self.assertNotIn(move('a3','b2'),r.actions(s))
        s=position(['c5'],['b4','h8'])
        self.assertNotIn(move('c5','a3',True),r.actions(s))
        s=position(['a1'],['h8'])
        self.assertEqual(r.actions(s),[move('a1','b2')])

    def test_capture_priority_and_chain_same_piece(self):
        r=CheckersRules(); s=position(['a3','h2'],['b4','d6','h8'])
        self.assertEqual(r.actions(s),[move('a3','c5',True)])
        t=r.play(s,r.actions(s)[0])
        self.assertEqual(t.board[sq('b4')],0)
        self.assertEqual(t.turn,1); self.assertEqual(t.active,sq('c5'))
        self.assertEqual(r.actions(t),[move('c5','e7',True)])
        t=r.play(t,r.actions(t)[0])
        self.assertEqual(t.turn,2); self.assertEqual(t.active,-1)
        self.assertEqual(t.board[sq('d6')],0)

    def test_capture_choice_no_maximum_rule(self):
        r=CheckersRules(); s=position(['a3','g3'],['b4','d6','f4','h8'])
        self.assertIn(move('a3','c5',True),r.actions(s))
        self.assertIn(move('g3','e5',True),r.actions(s))

    def test_kings_move_and_capture_backwards_but_do_not_fly(self):
        r=CheckersRules(); s=position([],['b4','h8'],kings_white=['c5'])
        self.assertIn(move('c5','a3',True),r.actions(s))
        t=r.play(s,move('c5','a3',True)); self.assertEqual(t.board[sq('a3')],-1)
        s=position([],['h8'],kings_white=['c5'])
        self.assertEqual(len(r.actions(s)),4)
        self.assertNotIn(move('c5','f8'),r.actions(s))

    def test_promotion_ends_turn_and_optional_continuation(self):
        r=CheckersRules(); s=position(['b6'],['c7','e7','h8'])
        a=move('b6','d8',True); t=r.play(s,a)
        self.assertEqual(t.board[sq('d8')],-1)
        self.assertEqual(t.turn,2)
        r=CheckersRules(False); t=r.play(s,a)
        self.assertEqual(t.turn,1); self.assertEqual(t.active,sq('d8'))
        self.assertIn(move('d8','f6',True),r.actions(t))
        s=position(['a1'],['g3'],turn=2)
        t=r.play(s,move('g3','h2')); self.assertEqual(t.board[sq('h2')],2)
        s=position(['h8'],['b2'],turn=2)
        t=r.play(s,move('b2','a1')); self.assertEqual(t.board[sq('a1')],-2)

    def test_game_end(self):
        r=CheckersRules(); s=position(['a3'],['b4'])
        self.assertEqual(r.terminal(r.play(s,move('a3','c5',True))),1)
        s=position(['a7'],['b8','c7'])
        self.assertEqual(r.actions(s),[])
        self.assertEqual(r.terminal(s),2)

    def test_search_full_chain_and_timeout_fallback(self):
        r=CheckersRules(); s=position(['a3'],['b4','d6'])
        for seconds in (0,0.2):
            plan,value,depth,nodes=search_checkers(r,s,seconds)
            self.assertEqual(plan,(move('a3','c5',True),move('c5','e7',True)))
            t=s
            for a in plan:
                self.assertIn(a,r.actions(t)); t=r.play(t,a)
            self.assertEqual(t.turn,2); self.assertEqual(r.terminal(t),1)
            if seconds: self.assertGreater(value,90000)
        s=position(['g5'],['h6'],turn=2)
        plan,value,*_=search_checkers(r,s,0.2)
        self.assertEqual(plan,(move('h6','f4',True),)); self.assertLess(value,-90000)

    def test_opening_search_is_legal(self):
        r=CheckersRules(); s=r.initial()
        plan,*_=search_checkers(r,s,0.1)
        self.assertEqual(len(plan),1); self.assertIn(plan[0],r.actions(s))

    def test_gui_clicks_chain_flip_editor_and_menu(self):
        import tkinter as tk
        from mainmenu import MainMenu
        root=tk.Tk(); root.withdraw(); menu=MainMenu(root)
        menu.open_game('checkers'); root.update()
        app=menu.games['checkers']; app.state=position(['a3'],['b4','d6','h8']); app.refresh()
        def click(name):
            x,y=app.coords(sq(name)); app.click(SimpleNamespace(x=x,y=y))
        click('a3'); click('c5')
        self.assertEqual(app.state.active,sq('c5'))
        click('e7'); self.assertEqual(app.state.turn,2)
        app.undo(); self.assertEqual(app.state.active,sq('c5'))
        app.plan=(move('c5','e7',True),); app.use_hint()
        self.assertEqual(app.state.board[sq('d6')],0)
        app.reset(); app.flip.set(True); root.update()
        click('b6'); self.assertEqual(app.selected,sq('b6'))
        click('a5'); self.assertEqual(app.state.board[sq('a5')],2)
        app.edit.set(True); app.edit_changed(); app.paint.set(-1); click('a3')
        self.assertEqual(app.state.board[sq('a3')],-1)
        # Remove one white man so the edited count remains at twelve.
        app.paint.set(0); click('b2')
        app.turn.set('Weiß'); app.commit()
        self.assertFalse(app.edit.get()); self.assertEqual(app.state.turn,1)
        self.assertEqual(app.state.board[sq('a3')],-1)
        menu.show_menu('checkers'); menu.open_game('checkers'); root.update()
        self.assertIs(app,menu.games['checkers'])
        self.assertEqual(app.state.board[sq('a3')],-1)
        root.destroy()

if __name__=='__main__': unittest.main()
