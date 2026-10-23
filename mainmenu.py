"""Main menu for the AC3 board-game companions."""
import tkinter as tk
from tkinter import ttk


class MainMenu:
    def __init__(self, root):
        self.root=root
        self.windows={}
        self.games={}
        root.title('AC3 · Brettspiel-Assistent')
        root.geometry('660x470')
        root.minsize(540,430)
        root.configure(bg='#14232b')
        panel=tk.Frame(root,bg='#14232b',padx=36,pady=30)
        panel.pack(fill='both',expand=True)
        tk.Label(panel,text='AC3 · BRETT SPIELEN',bg='#14232b',fg='#f3e9cf',
                 font=('Segoe UI',23,'bold')).pack(anchor='w')
        tk.Label(panel,text='Wähle deinen Spielassistenten.',bg='#14232b',fg='#c1d1d5',
                 font=('Segoe UI',12)).pack(anchor='w',pady=(8,24))
        ttk.Button(panel,text='Mühle öffnen · 6er / 9er / 12er',
                   command=lambda:self.open_game('morris')).pack(fill='x',ipady=12)
        tk.Label(panel,text='Züge berechnen, Mühlen bilden und Schlagziele anzeigen.',
                 bg='#14232b',fg='#c1d1d5',wraplength=560,justify='left').pack(anchor='w',pady=(7,20))
        ttk.Button(panel,text='Fanorona öffnen',
                   command=lambda:self.open_game('fanorona')).pack(fill='x',ipady=12)
        tk.Label(panel,text='Annäherung, Rückzug und Schlagketten auf dem 9 × 5-Brett.',
                 bg='#14232b',fg='#c1d1d5',wraplength=560,justify='left').pack(anchor='w',pady=(7,20))
        ttk.Button(panel,text='Beenden',command=root.destroy).pack(anchor='e',pady=(10,0))
        tk.Label(panel,text='Manuell mit AC3 abgleichen · Empfehlungen ohne Gewinngarantie',
                 bg='#14232b',fg='#c1d1d5',wraplength=560).pack(anchor='w',side='bottom')

    def open_game(self, name):
        if name not in ('morris','fanorona'): raise ValueError('Unbekanntes Spiel')
        window=self.windows.get(name)
        if window is None or not window.winfo_exists():
            window=tk.Toplevel(self.root)
            self.windows[name]=window
            callback=lambda:self.show_menu(name)
            if name=='morris':
                from morris import App
                game=App(window,back_to_menu=callback)
            else:
                from fanorona import FanoronaApp
                game=FanoronaApp(window,back_to_menu=callback)
            self.games[name]=game
            window.protocol('WM_DELETE_WINDOW',callback)
        self.root.withdraw()
        window.deiconify()
        window.lift()

    def show_menu(self, name):
        window=self.windows.get(name)
        if window is not None and window.winfo_exists(): window.withdraw()
        self.root.deiconify()
        self.root.lift()


def main():
    root=tk.Tk()
    MainMenu(root)
    root.mainloop()


if __name__=='__main__':
    main()
