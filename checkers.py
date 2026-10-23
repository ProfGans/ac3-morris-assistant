"""AC3 checkers companion: English draughts with compulsory multiple jumps."""
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
from fanorona import search_fanorona

POINTS=tuple((x,y) for y in range(8) for x in range(8))
NAMES=tuple(f'{"abcdefgh"[x]}{8-y}' for x,y in POINTS)
PLAYABLE=tuple(i for i,(x,y) in enumerate(POINTS) if (x+y)%2==1)
# Men: 1 = white, 2 = black; kings: -1 = white, -2 = black.

@dataclass(frozen=True)
class CheckersState:
    board: tuple
    turn: int = 2
    active: int = -1

class CheckersRules:
    def __init__(self,crown_ends_turn=True):
        self.crown_ends_turn=crown_ends_turn

    def initial(self):
        b=[0]*64
        for i in PLAYABLE:
            y=POINTS[i][1]
            if y<3: b[i]=2
            elif y>4: b[i]=1
        return CheckersState(tuple(b))

    def directions(self,piece):
        ys=(-1,1) if piece<0 else ((-1,) if piece==1 else (1,))
        return tuple((dx,dy) for dy in ys for dx in (-1,1))

    def captured(self,s,a):
        src,dst,mode=a
        return ((src+dst)//2,) if mode=='J' else ()

    def captures(self,s):
        result=[]
        pieces=(s.active,) if s.active>=0 else PLAYABLE
        for i in pieces:
            piece=s.board[i]
            if abs(piece)!=s.turn: continue
            x,y=POINTS[i]
            for dx,dy in self.directions(piece):
                tx,ty=x+2*dx,y+2*dy
                if not (0<=tx<8 and 0<=ty<8): continue
                middle=(y+dy)*8+x+dx; dst=ty*8+tx
                if abs(s.board[middle])==3-s.turn and s.board[dst]==0:
                    result.append((i,dst,'J'))
        return result

    def actions(self,s):
        jumps=self.captures(s)
        if jumps or s.active>=0: return jumps
        moves=[]
        for i in PLAYABLE:
            if abs(s.board[i])!=s.turn: continue
            x,y=POINTS[i]
            for dx,dy in self.directions(s.board[i]):
                tx,ty=x+dx,y+dy
                if 0<=tx<8 and 0<=ty<8 and not s.board[ty*8+tx]:
                    moves.append((i,ty*8+tx,'P'))
        return moves

    def play(self,s,a):
        src,dst,mode=a; b=list(s.board); piece=b[src]; b[src]=0; b[dst]=piece
        for i in self.captured(s,a): b[i]=0
        promoted=piece>0 and POINTS[dst][1]==(0 if s.turn==1 else 7)
        if promoted: b[dst]=-piece
        if mode=='J' and not (promoted and self.crown_ends_turn):
            t=CheckersState(tuple(b),s.turn,dst)
            if self.captures(t): return t
        return CheckersState(tuple(b),3-s.turn)

    def terminal(self,s):
        if not any(abs(v)==1 for v in s.board): return 2
        if not any(abs(v)==2 for v in s.board): return 1
        if not self.actions(s): return 3-s.turn
        return None

    def evaluate(self,s):
        value=0
        for i,piece in enumerate(s.board):
            if not piece: continue
            x,y=POINTS[i]; owner=abs(piece); sign=1 if owner==1 else -1
            score=185 if piece<0 else 100+(7-y if owner==1 else y)*5
            score+=int(2<=x<=5 and 2<=y<=5)*7
            if piece>0 and y==(7 if owner==1 else 0): score+=5
            value+=sign*score
        return value


def search_checkers(rules,state,seconds):
    """The shared timed alpha-beta search handles same-player jump continuations."""
    plan,value,depth,nodes=search_fanorona(rules,state,seconds)
    if depth==0 and plan:
        # Finish compulsory jumps even when the budget expires before depth one.
        t=rules.play(state,plan[0]); steps=list(plan)
        while t.turn==state.turn and rules.terminal(t) is None:
            a=max(rules.actions(t),key=lambda a:len(rules.captured(t,a)))
            steps.append(a); t=rules.play(t,a)
        plan=tuple(steps)
    return plan,value,depth,nodes


class CheckersApp:
    def __init__(self,root,back_to_menu=None):
        self.root=root; root.title('AC3 · Dame-Assistent'); root.geometry('1100x900')
        self.state=CheckersRules().initial(); self.history=[]; self.selected=None; self.plan=()
        self.version=0; self.busy=False; self.results=queue.Queue()
        self.edit=tk.BooleanVar(value=False); self.paint=tk.IntVar(value=1)
        self.turn=tk.StringVar(value='Schwarz'); self.seconds=tk.StringVar(value='5')
        self.flip=tk.BooleanVar(value=False); self.crown_ends_turn=tk.BooleanVar(value=True)
        frame=ttk.Frame(root,padding=16); frame.pack(fill='both',expand=True)
        header=ttk.Frame(frame); header.pack(fill='x')
        ttk.Label(header,text='AC3 · DAME',font=('Segoe UI',22,'bold')).pack(side='left')
        if back_to_menu is not None:
            ttk.Button(header,text='← Hauptmenü',command=back_to_menu).pack(side='right')
        ttk.Label(frame,text='Eigenen Stein → Zielfeld anklicken. D = Dame · Grün = mögliche Ziele · Rot = Schlagziel.').pack(anchor='w',pady=8)
        body=ttk.Frame(frame); body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,bg='#14232b',highlightthickness=0,width=720,height=730)
        self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw()); self.canvas.bind('<Button-1>',self.click)
        side=ttk.Frame(body,padding=(14,0)); side.pack(side='right',fill='y')
        self.status=tk.StringVar(); ttk.Label(side,textvariable=self.status,font=('Segoe UI',12,'bold'),wraplength=290).pack(anchor='w',pady=8)
        ttk.Label(side,text='Rechenzeit (Sekunden)').pack(anchor='w')
        ttk.Combobox(side,textvariable=self.seconds,values=['1','5','15','30','60'],width=10,state='readonly').pack(anchor='w',pady=5)
        self.calc=ttk.Button(side,text='Besten Zug / Schlagkette berechnen',command=self.calculate); self.calc.pack(fill='x',pady=4)
        self.apply=ttk.Button(side,text='Nächsten empfohlenen Schritt übernehmen',command=self.use_hint); self.apply.pack(fill='x',pady=4)
        ttk.Button(side,text='Schritt zurück',command=self.undo).pack(fill='x',pady=4)
        ttk.Button(side,text='Neues Spiel',command=self.reset).pack(fill='x',pady=4)
        ttk.Checkbutton(side,text='Brett drehen (Schwarz unten)',variable=self.flip,command=self.draw).pack(anchor='w',pady=4)
        self.info=tk.StringVar(value='Schwarz beginnt. Weiß zieht nach oben, Schwarz nach unten. Schlagen und vollständige Schlagketten sind Pflicht.')
        self.details=ScrolledText(side,width=40,height=7,wrap='word',font=('Segoe UI',9),state='disabled'); self.details.pack(fill='x',pady=10)
        def update_details(*_):
            self.details.configure(state='normal'); self.details.delete('1.0','end')
            self.details.insert('1.0',self.info.get()); self.details.configure(state='disabled')
        self.info.trace_add('write',update_details); update_details()
        ttk.Separator(side).pack(fill='x',pady=8)
        ttk.Checkbutton(side,text='Stellung bearbeiten',variable=self.edit,command=self.edit_changed).pack(anchor='w')
        for p,name in ((1,'Weißer Stein'),(-1,'Weiße Dame'),(2,'Schwarzer Stein'),(-2,'Schwarze Dame'),(0,'Feld leeren')):
            ttk.Radiobutton(side,text=name,variable=self.paint,value=p).pack(anchor='w')
        ttk.Label(side,text='Am Zug:').pack(anchor='w')
        ttk.Combobox(side,textvariable=self.turn,values=['Weiß','Schwarz'],state='readonly',width=12).pack(anchor='w',pady=4)
        ttk.Button(side,text='Stellung als neuen Zug anwenden',command=self.commit).pack(fill='x',pady=4)
        ttk.Checkbutton(side,text='Umwandlung beendet den Zug',variable=self.crown_ends_turn,command=self.rules_changed).pack(anchor='w',pady=5)
        ttk.Label(side,text='Englische Dame / Checkers: kurze Damen,\nSteine ziehen und schlagen nur vorwärts.\nSuch-KI ohne Gewinngarantie.',wraplength=290).pack(anchor='w',pady=6)
        self.refresh(); self.timer=root.after(100,self.poll)
        root.bind('<Destroy>',self.destroyed,add='+')

    def destroyed(self,event):
        if event.widget==self.root:
            try: self.root.after_cancel(self.timer)
            except tk.TclError: pass

    def rules(self): return CheckersRules(self.crown_ends_turn.get())
    def invalidate(self): self.version+=1; self.plan=(); self.selected=None
    def layout(self):
        w=max(160,self.canvas.winfo_width()); h=max(160,self.canvas.winfo_height())
        step=min(w-56,h-56)/8
        return (w-8*step)/2,(h-8*step)/2,step
    def coords(self,i):
        ox,oy,step=self.layout(); x,y=POINTS[i]
        if self.flip.get(): x,y=7-x,7-y
        return ox+(x+.5)*step,oy+(y+.5)*step
    def refresh(self):
        s=self.state; winner=self.rules().terminal(s); name='Weiß' if s.turn==1 else 'Schwarz'
        text=f'{"Weiß" if winner==1 else "Schwarz"} gewinnt.' if winner else name+(': Schlagkette fortsetzen' if s.active>=0 else ': am Zug')
        counts=[sum(abs(v)==p for v in s.board) for p in (1,2)]
        kings=[s.board.count(-p) for p in (1,2)]
        self.status.set(text+f'\nSteine gesamt W / S: {counts[0]} / {counts[1]}\nDavon Damen W / S: {kings[0]} / {kings[1]}')
        self.turn.set(name)
        self.apply.configure(state='normal' if self.plan and not self.edit.get() else 'disabled')
        self.draw()
    def draw(self):
        c=self.canvas; c.delete('all'); rules=self.rules(); ox,oy,step=self.layout()
        targets={a[1] for a in rules.actions(self.state) if a[0]==self.selected}
        captured=rules.captured(self.state,self.plan[0]) if self.plan else ()
        for i,(x,y) in enumerate(POINTS):
            cx,cy=self.coords(i); dark=i in PLAYABLE
            c.create_rectangle(cx-step/2,cy-step/2,cx+step/2,cy+step/2,fill='#50616a' if dark else '#d4c7ae',outline='')
            if not dark: continue
            c.create_text(cx-step*.37,cy-step*.35,text=NAMES[i],fill='#cbd8db',font=('Segoe UI',8))
            if i in targets: c.create_oval(cx-step*.16,cy-step*.16,cx+step*.16,cy+step*.16,fill='#56dbc1',outline='')
            v=self.state.board[i]
            if v:
                radius=step*.33
                outline='#ff706c' if i in captured else ('#f4b85d' if i in (self.selected,self.state.active) else '#a78652')
                c.create_oval(cx-radius,cy-radius,cx+radius,cy+radius,fill='#f3e9cf' if abs(v)==1 else '#1c1b22',outline=outline,width=3)
                if v<0: c.create_text(cx,cy,text='D',fill='#1c1b22' if abs(v)==1 else '#f3e9cf',font=('Segoe UI',int(max(10,step*.25)),'bold'))
                if i in captured: c.create_text(cx,cy,text='×',fill='#ff706c',font=('Segoe UI',int(max(12,step*.4)),'bold'))
        if self.plan:
            a=self.plan[0]; c.create_line(*self.coords(a[0]),*self.coords(a[1]),fill='#56dbc1',width=4,arrow='last')
        for x in range(8):
            col=7-x if self.flip.get() else x
            c.create_text(ox+(x+.5)*step,oy+8*step+14,text='abcdefgh'[col],fill='#c1d1d5')
        for y in range(8):
            rank=y+1 if self.flip.get() else 8-y
            c.create_text(ox-14,oy+(y+.5)*step,text=str(rank),fill='#c1d1d5')
    def click(self,event):
        ox,oy,step=self.layout(); x=int((event.x-ox)//step); y=int((event.y-oy)//step)
        if not (0<=x<8 and 0<=y<8): return
        if self.flip.get(): x,y=7-x,7-y
        i=y*8+x
        if i not in PLAYABLE: return
        if self.edit.get():
            b=list(self.state.board); b[i]=self.paint.get()
            self.state=CheckersState(tuple(b),self.state.turn); self.invalidate(); self.refresh(); return
        if self.rules().terminal(self.state) is not None: return
        if abs(self.state.board[i])==self.state.turn:
            if self.state.active>=0 and i!=self.state.active:
                self.info.set('Die Schlagkette muss mit demselben Stein fortgesetzt werden.'); return
            self.selected=i; self.refresh(); return
        source=self.state.active if self.state.active>=0 else self.selected
        a=next((a for a in self.rules().actions(self.state) if a[:2]==(source,i)),None)
        if a: self.move(a)
        else: self.info.set('Kein erlaubter Zug. Erst eigenen Stein, dann grünes Zielfeld wählen. Schlagen hat Vorrang; Schlagketten müssen beendet werden.')
    def describe(self,a,s):
        victims=self.rules().captured(s,a)
        promoted=s.board[a[0]]>0 and POINTS[a[1]][1]==(0 if s.turn==1 else 7)
        return f'{NAMES[a[0]]} → {NAMES[a[1]]}'+(' · nimm '+', '.join(NAMES[i] for i in victims) if victims else '')+(' · wird Dame' if promoted else '')
    def show_plan(self,depth=None,nodes=None):
        state=self.state; lines=[]
        for n,a in enumerate(self.plan,1):
            lines.append(f'{n}. '+self.describe(a,state)); state=self.rules().play(state,a)
        if depth is not None: lines.append(f'Suchtiefe: {depth} Züge · {nodes:,} Stellungen')
        self.info.set('\n'.join(lines)); self.refresh()
    def move(self,a):
        r=self.rules()
        if self.edit.get() or r.terminal(self.state) is not None or a not in r.actions(self.state): return
        description=self.describe(a,self.state)
        self.history.append(self.state); self.state=r.play(self.state,a); self.invalidate()
        self.selected=self.state.active if self.state.active>=0 else None
        self.info.set(description+('\nMit diesem Stein weiterschlagen.' if self.state.active>=0 else ''))
        self.refresh()
    def use_hint(self):
        if not self.plan: return
        a,rest=self.plan[0],self.plan[1:]; oldturn=self.state.turn
        self.move(a)
        if self.state.turn==oldturn: self.plan=rest
        if self.plan: self.show_plan()
    def undo(self):
        if self.history:
            self.state=self.history.pop(); self.invalidate(); self.selected=self.state.active if self.state.active>=0 else None
            self.info.set('Letzten Schritt zurückgenommen.'); self.refresh()
    def reset(self):
        self.state=self.rules().initial(); self.history=[]; self.edit.set(False); self.invalidate()
        self.info.set('Neue Partie: Schwarz beginnt. Bei Bedarf im Editor Weiß als Startspieler wählen.'); self.refresh()
    def edit_changed(self):
        if self.edit.get() and self.state.active>=0:
            self.history.append(self.state); self.state=CheckersState(self.state.board,self.state.turn)
        self.invalidate(); self.info.set('Editor: Stellung zu Beginn eines Zuges eintragen. Weiße Steine ziehen nach oben, schwarze nach unten. Damen gesondert wählen.'); self.refresh()
    def commit(self):
        b=list(self.state.board)
        if any(sum(abs(v)==p for v in b)>12 for p in (1,2)) or not all(any(abs(v)==p for v in b) for p in (1,2)):
            messagebox.showerror('Ungültige Stellung','Je Farbe 1 bis 12 Steine einschließlich Damen eintragen.',parent=self.root); return
        for i in PLAYABLE:
            if b[i]==1 and POINTS[i][1]==0: b[i]=-1
            elif b[i]==2 and POINTS[i][1]==7: b[i]=-2
        self.history.append(self.state); self.state=CheckersState(tuple(b),1 if self.turn.get()=='Weiß' else 2)
        self.edit.set(False); self.invalidate(); self.info.set('Stellung übernommen: Beginn eines neuen Zuges.'); self.refresh()
    def rules_changed(self): self.invalidate(); self.info.set('Umwandlungsregel geändert. Bitte neu berechnen.'); self.refresh()
    def calculate(self):
        if self.busy or self.edit.get() or self.rules().terminal(self.state) is not None: return
        self.busy=True; self.calc.configure(state='disabled'); self.info.set('Zug und vollständige Schlagkette werden berechnet …')
        version=self.version; state=self.state; rules=self.rules(); seconds=float(self.seconds.get())
        def work():
            try: result=search_checkers(rules,state,seconds)
            except Exception as exc: result=exc
            self.results.put((version,result))
        threading.Thread(target=work,daemon=True).start()
    def poll(self):
        try:
            version,result=self.results.get_nowait(); self.busy=False; self.calc.configure(state='normal')
            if version==self.version:
                if isinstance(result,Exception): self.info.set(f'Berechnung fehlgeschlagen: {result}')
                else:
                    self.plan,value,depth,nodes=result; self.show_plan(depth,nodes)
            else: self.info.set('Stellung geändert. Bitte neu berechnen.')
        except queue.Empty: pass
        self.timer=self.root.after(100,self.poll)

if __name__=='__main__':
    root=tk.Tk(); CheckersApp(root); root.mainloop()
