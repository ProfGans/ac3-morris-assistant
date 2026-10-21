import unittest
from types import SimpleNamespace
from fanorona import FanoronaRules, FanoronaState, FanoronaApp, STOP, search_fanorona

def state(white,black,**kwargs):
    b=[0]*45
    for i in white: b[i]=1
    for i in black: b[i]=2
    return FanoronaState(tuple(b),**kwargs)

class FanoronaTests(unittest.TestCase):
    def test_initial(self):
        r=FanoronaRules(); s=r.initial()
        self.assertEqual((s.board.count(1),s.board.count(2),s.board.count(0)),(22,22,1))
        self.assertEqual(s.board[22],0)
        self.assertTrue(r.actions(s))
        self.assertTrue(all(a[2] in ('A','W') and a[1]==22 for a in r.actions(s)))
        self.assertIn((21,22,'A'),r.actions(s)); self.assertIn((21,22,'W'),r.actions(s))

    def test_edges(self):
        r=FanoronaRules()
        self.assertIn(10,r.adj[0]); self.assertNotIn(11,r.adj[1])
        for i,neighbours in enumerate(r.adj):
            for j in neighbours: self.assertIn(i,r.adj[j])

    def test_capturing_line_and_gap(self):
        r=FanoronaRules(); s=state([20],[19,22,23,25])
        self.assertEqual(r.captured(s,(20,21,'A')),(22,23))
        self.assertEqual(r.captured(s,(20,21,'W')),(19,))
        for mode,victims,survivors in [('A',(22,23),(19,25)),('W',(19,),(22,23,25))]:
            self.assertIn((20,21,mode),r.actions(s))
            t=r.play(s,(20,21,mode))
            for i in victims: self.assertEqual(t.board[i],0)
            for i in survivors: self.assertEqual(t.board[i],2)
            self.assertEqual(t.board[21],1)
        self.assertTrue(all(a[2]!='P' for a in r.actions(s)))

    def test_chain_direction_visited_and_same_piece(self):
        r=FanoronaRules(); s=state([20,40],[22,23,3,43])
        t=r.play(s,(20,21,'A'))
        self.assertEqual(t.active,21); self.assertEqual(t.turn,1)
        self.assertEqual(t.visited,(20,21))
        self.assertIn((21,12,'A'),r.actions(t))
        self.assertTrue(all(a==STOP or a[0]==21 for a in r.actions(t)))
        self.assertNotIn((21,22,'W'),r.actions(t))
        restricted=FanoronaState(t.board,1,21,(20,21,12),(1,0))
        self.assertFalse(any(a[1]==12 for a in r.actions(restricted) if a!=STOP))
        self.assertIn(STOP,r.actions(t))
        self.assertNotIn(STOP,FanoronaRules(True).actions(t))
        stopped=r.play(t,STOP)
        self.assertEqual(stopped.turn,2); self.assertEqual(stopped.active,-1)
        self.assertEqual(stopped.visited,())

    def test_paika_and_terminal(self):
        r=FanoronaRules(); s=state([0],[44])
        self.assertTrue(all(a[2]=='P' for a in r.actions(s)))
        self.assertEqual(r.play(s,(0,1,'P')).turn,2)
        s=state([20],[22,23])
        t=r.play(s,(20,21,'A'))
        self.assertEqual(r.terminal(t),1)

    def test_search_complete_legal_plan(self):
        for mandatory in (False,True):
            r=FanoronaRules(mandatory)
            s=state([20],[22,23,3,12])
            plan,value,depth,nodes=search_fanorona(r,s,0.15)
            self.assertTrue(plan); self.assertGreater(depth,0)
            for a in plan:
                self.assertIn(a,r.actions(s)); s=r.play(s,a)
            self.assertEqual(s.turn,2)
            self.assertEqual(r.terminal(s),1)
            self.assertGreater(value,90000)

    def test_direction_cannot_repeat_even_with_new_capture(self):
        r=FanoronaRules()
        # Moving right by withdrawal would capture a stone but repeats the last direction.
        s=state([21],[20,3],active=21,visited=(12,21),direction=(1,0))
        self.assertEqual(r.captured(s,(21,22,'W')),(20,))
        self.assertNotIn((21,22,'W'),r.actions(s))
        self.assertIn((21,12,'A'),r.actions(FanoronaState(s.board,1,21,(21,),(1,0))))

    def test_black_capture(self):
        r=FanoronaRules(); s=state([22,23],[20],turn=2)
        plan,value,depth,nodes=search_fanorona(r,s,0.1)
        self.assertEqual(plan,((20,21,'A'),))
        self.assertLess(value,-90000)
        self.assertEqual(r.terminal(r.play(s,plan[0])),2)

    def test_opening_search_budget(self):
        r=FanoronaRules(); s=r.initial()
        plan,*_=search_fanorona(r,s,0.1)
        self.assertTrue(plan)
        for a in plan:
            self.assertIn(a,r.actions(s)); s=r.play(s,a)
        tiny,*_=search_fanorona(r,r.initial(),0)
        self.assertIn(tiny[0],r.actions(r.initial()))

    def test_gui_choice_capture_undo_and_integration(self):
        import tkinter as tk
        from morris import App
        root=tk.Tk(); root.withdraw(); parent=App(root)
        parent.open_fanorona(); app=parent.fanorona_app; root.update()
        app.state=state([20],[19,22,23,25]); app.refresh()
        for i in (20,21):
            x,y=app.coords(i); app.click(SimpleNamespace(x=x,y=y))
        self.assertEqual(len(app.choice),2)
        app.choose('A')
        self.assertEqual(app.state.board[22],0)
        self.assertEqual(app.state.board[19],2)
        app.undo(); self.assertEqual(app.state.board[22],2)
        app.plan=((20,21,'W'),); app.use_hint()
        self.assertEqual(app.state.board[19],0)
        app.reset(); self.assertEqual(app.state,app.rules().initial())
        app.edit.set(True); app.edit_changed(); app.paint.set(0)
        x,y=app.coords(0); app.click(SimpleNamespace(x=x,y=y))
        self.assertEqual(app.state.board[0],0)
        app.turn.set('Schwarz'); app.commit(); self.assertEqual(app.state.turn,2)
        self.assertFalse(app.edit.get())
        parent.open_fanorona(); self.assertIs(app,parent.fanorona_app)
        parent.fanorona_window.destroy(); root.update(); root.destroy()

if __name__=='__main__': unittest.main()
