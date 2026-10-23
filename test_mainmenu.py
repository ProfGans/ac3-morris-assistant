import tkinter as tk
import unittest
from mainmenu import MainMenu

class MainMenuTests(unittest.TestCase):
    def test_game_selection_return_and_resume(self):
        root=tk.Tk(); menu=MainMenu(root); root.update()
        self.assertEqual(root.title(),'AC3 · Brettspiel-Assistent')
        menu.open_game('morris'); root.update()
        game=menu.games['morris']; window=menu.windows['morris']
        game.move((-1,0))
        self.assertEqual(root.state(),'withdrawn')
        self.assertEqual(window.state(),'normal')
        menu.show_menu('morris'); root.update()
        self.assertEqual(root.state(),'normal')
        self.assertEqual(window.state(),'withdrawn')
        menu.open_game('fanorona'); root.update()
        self.assertEqual(menu.games['fanorona'].state.board.count(1),22)
        self.assertEqual(root.state(),'withdrawn')
        menu.show_menu('fanorona'); menu.open_game('morris'); root.update()
        self.assertIs(menu.games['morris'],game)
        self.assertEqual(game.state.board[0],1)
        self.assertEqual(len(menu.windows),2)
        root.destroy()

    def test_close_callback_returns_to_menu(self):
        root=tk.Tk(); menu=MainMenu(root)
        menu.open_game('fanorona'); root.update()
        window=menu.windows['fanorona']
        window.tk.call(window.protocol('WM_DELETE_WINDOW'))
        root.update()
        self.assertEqual(root.state(),'normal')
        self.assertTrue(window.winfo_exists())
        self.assertEqual(window.state(),'withdrawn')
        root.destroy()

if __name__=='__main__': unittest.main()
