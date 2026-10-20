import unittest
from morris import State, Rules, search

class MorrisTests(unittest.TestCase):
    def test_board(self):
        r=Rules()
        self.assertEqual(len(r.mills),20)
        self.assertEqual(len(r.actions(State())),24)
        self.assertIn(8,r.adj[0])
    def test_capture_protection(self):
        b=[0]*24
        for i in (0,1): b[i]=1
        for i in (8,9,10,12): b[i]=2
        r=Rules(); s=r.play(State(tuple(b),(10,8)),(-1,2))
        self.assertTrue(s.capture)
        self.assertEqual(r.actions(s),[(-2,12)])
        s=r.play(s,(-2,12))
        self.assertEqual(s.turn,2)
        self.assertEqual(s.reserve,(9,8))
    def test_fly(self):
        b=[0]*24
        for i in (0,2,4): b[i]=1
        for i in (8,10,12,14): b[i]=2
        s=State(tuple(b),(0,0))
        self.assertIn((0,23),Rules().actions(s))
        self.assertNotIn((0,23),Rules(flying=False).actions(s))
    def test_diagonal_option(self):
        b=[0]*24
        for i in (0,8,16): b[i]=1
        self.assertTrue(Rules().mill(b,0,1))
        self.assertFalse(Rules(False).mill(b,0,1))
    def test_search_wins(self):
        b=[0]*24
        for i in (0,1,3,6): b[i]=1
        for i in (8,10,12): b[i]=2
        r=Rules(); s=State(tuple(b),(0,0))
        action,score,depth,nodes=search(r,s,0.5)
        self.assertIn(action,r.actions(s))
        self.assertGreater(score,90000)
    def test_mill_recommendation_includes_capture(self):
        b=[0]*24
        for i in (0,1,3,6): b[i]=1
        for i in (8,10,12): b[i]=2
        r=Rules(); state=State(tuple(b),(0,0))
        move,score,depth,nodes,capture=search(r,state,0.5,include_capture=True)
        after=r.play(state,move)
        self.assertTrue(after.capture)
        self.assertIsNotNone(capture)
        self.assertIn(capture,r.actions(after))
        self.assertEqual(r.terminal(r.play(after,capture)),1)

    def test_gui_capture_continuation(self):
        import tkinter as tk
        from morris import App
        root=tk.Tk(); root.withdraw()
        app=App(root)
        b=[0]*24
        for i in (0,1): b[i]=1
        for i in (8,9,10,12): b[i]=2
        app.state=State(tuple(b),(10,8))
        app.hint=(-1,2); app.capture_hint=(-2,12)
        app.use_hint()
        self.assertTrue(app.state.capture)
        self.assertEqual(app.hint,(-2,12))
        self.assertIn('f2',app.info.get())
        app.use_hint()
        self.assertEqual(app.state.board[12],0)
        self.assertEqual(app.state.turn,2)
        root.destroy()

    def test_click_capture_and_editor(self):
        import tkinter as tk
        from types import SimpleNamespace
        from morris import App
        root=tk.Tk()
        app=App(root); root.update()
        b=[0]*24
        for i in (0,1): b[i]=1
        for i in (8,9,10,12): b[i]=2
        app.state=State(tuple(b),(10,8))
        app.hint=(-1,2); app.capture_hint=(-2,12)
        x,y=app.coords(12)
        app.click(SimpleNamespace(x=x,y=y))
        self.assertEqual(app.state.board[2],1)
        self.assertEqual(app.state.board[12],0)
        self.assertEqual(app.state.turn,2)
        # Imported mill position with an outstanding capture.
        b[2]=1
        app.state=State(tuple(b),(9,8))
        app.refresh(); app.pending_capture.set(True); app.commit()
        self.assertTrue(app.state.capture)
        # Protected mill cannot be captured while a loose stone exists.
        x,y=app.coords(8); app.click(SimpleNamespace(x=x,y=y))
        self.assertEqual(app.state.board[8],2)
        self.assertTrue(app.state.capture)
        x,y=app.coords(12); app.click(SimpleNamespace(x=x,y=y))
        self.assertEqual(app.state.board[12],0)
        self.assertFalse(app.state.capture)
        root.destroy()

    def test_variant_boards_and_movement(self):
        for variant,points,mills in ((6,16,8),(9,24,16),(12,24,20)):
            with self.subTest(variant=variant):
                r=Rules(variant=variant)
                self.assertEqual(r.initial().reserve,(variant,variant))
                self.assertEqual(len(r.points),points)
                self.assertEqual(len(r.mills),mills)
                self.assertEqual(len(r.actions(r.initial())),points)
                self.assertEqual(8 in r.adj[0],variant==12)
                self.assertIn(9,r.adj[1])
                self.assertTrue(all(j in r.points for i in r.points for j in r.adj[i]))
                action,*_=search(r,r.initial(),0.03)
                self.assertIn(action,r.actions(r.initial()))
        b=[0]*24
        for i in (0,1,2): b[i]=1
        self.assertTrue(Rules(variant=6).mill(b,0,1))
        for i in (1,9,17): b[i]=2
        self.assertFalse(Rules(variant=6).mill(b,9,2))
        self.assertTrue(Rules(variant=9).mill(b,9,2))

    def test_variant_switch_resets_state(self):
        import tkinter as tk
        from morris import App
        root=tk.Tk(); root.withdraw(); app=App(root)
        for variant in (6,9,12):
            app.variant.set(f'{variant}er-Mühle'); app.variant_changed()
            self.assertEqual(app.state.reserve,(variant,variant))
            self.assertEqual(app.state.board,(0,)*24)
            self.assertEqual(app.history,[])
            self.assertIsNone(app.hint)
            self.assertEqual(app.diagonal.get(),variant==12)
            self.assertEqual(str(app.diagonal_control.cget('state')),'normal' if variant==12 else 'disabled')
            app.move((-1,0))
            app.undo()
            self.assertEqual(app.state,app.rules().initial())
        root.destroy()

    def test_gui(self):
        import tkinter as tk
        from morris import App
        root=tk.Tk(); root.withdraw()
        app=App(root); root.update(); app.calculate()
        root.destroy()

if __name__=='__main__': unittest.main()

