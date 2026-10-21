import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass

# Ring order: top left, top middle, top right, right middle,
# bottom right, bottom middle, bottom left, left middle.
POINTS = [(x,y) for d in (0,1,2) for x,y in
          [(d,d),(3,d),(6-d,d),(6-d,3),(6-d,6-d),(3,6-d),(d,6-d),(d,3)]]
NAMES = [f'{"abcdefg"[x]}{7-y}' for x,y in POINTS]
BASE = [tuple(r*8+i for i in side) for r in range(3)
        for side in ((0,1,2),(2,3,4),(4,5,6),(6,7,0))]
LINKS = [tuple(r*8+i for r in range(3)) for i in range(8)]

@dataclass(frozen=True)
class State:
    board: tuple = (0,)*24
    reserve: tuple = (12,12)
    turn: int = 1
    capture: bool = False

class Rules:
    def __init__(self, diagonal=True, flying=True, variant=12):
        if variant not in (6,9,12): raise ValueError('Unbekannte Variante')
        self.variant=variant
        self.points=tuple(range(16 if variant==6 else 24))
        sides=[m for m in BASE if all(i in self.points for i in m)]
        connectors=[tuple(i for i in line if i in self.points)
                    for n,line in enumerate(LINKS) if n%2 or variant==12]
        self.lines=sides+connectors
        self.mills=sides+[m for n,m in enumerate(LINKS)
                          if variant!=6 and (n%2 or (variant==12 and diagonal))]
        self.flying=flying
        self.adj = [set() for _ in range(24)]
        for line in self.lines:
            for a,b in zip(line,line[1:]):
                self.adj[a].add(b); self.adj[b].add(a)
        self.at = [[m for m in self.mills if i in m] for i in range(24)]

    def initial(self):
        return State(reserve=(self.variant,self.variant))

    def mill(self,b,i,p):
        return any(all(b[j]==p for j in m) for m in self.at[i])

    def actions(self,s):
        b,p=s.board,s.turn
        if s.capture:
            enemies=[i for i,v in enumerate(b) if v==3-p]
            loose=[i for i in enemies if not self.mill(b,i,3-p)]
            return [(-2,i) for i in (loose or enemies)]
        if s.reserve[p-1]:
            return [(-1,i) for i in self.points if not b[i]]
        if b.count(p)<3: return []
        empty=[i for i in self.points if not b[i]]
        fly=self.flying and b.count(p)==3
        return [(i,j) for i,v in enumerate(b) if v==p
                for j in (empty if fly else self.adj[i]) if not b[j]]

    def play(self,s,a):
        src,dst=a; b=list(s.board); r=list(s.reserve); p=s.turn
        if src==-2:
            b[dst]=0
            return State(tuple(b),tuple(r),3-p)
        if src==-1: r[p-1]-=1
        else: b[src]=0
        b[dst]=p
        capture=self.mill(b,dst,p) and (3-p in b)
        return State(tuple(b),tuple(r),p if capture else 3-p,capture)

    def terminal(self,s):
        if s.capture: return None
        for p in (1,2):
            if not s.reserve[p-1] and s.board.count(p)<3: return 3-p
        if not self.actions(s):
            if not any(s.reserve) and all(s.board[i] for i in self.points): return 0
            return 3-s.turn
        return None

    def evaluate(self,s):
        b=s.board
        score=0
        for p,sign in ((1,1),(2,-1)):
            score+=sign*120*(b.count(p)+s.reserve[p-1])
            for m in self.mills:
                v=[b[i] for i in m]
                if 3-p not in v:
                    score+=sign*([0,3,26,48][v.count(p)])
            score+=sign*sum(len([j for j in self.adj[i] if not b[j]]) for i,v in enumerate(b) if v==p)*2
        return score

def search(rules,state,seconds,include_capture=False):
    deadline=time.monotonic()+seconds
    nodes=0
    def visit(s,depth,alpha,beta,path):
        nonlocal nodes
        nodes+=1
        if time.monotonic()>=deadline: raise TimeoutError
        winner=rules.terminal(s)
        if winner is not None: return (0 if winner==0 else (100000+depth if winner==1 else -100000-depth)),()
        if s in path: return 0,()
        if depth<=0 and not s.capture: return rules.evaluate(s),()
        moves=rules.actions(s)
        children=[(a,rules.play(s,a)) for a in moves]
        children.sort(key=lambda item:rules.evaluate(item[1]),reverse=s.turn==1)
        best=-float('inf') if s.turn==1 else float('inf'); chosen=()
        for a,child in children:
            value,continuation=visit(child,depth-(child.turn!=s.turn),alpha,beta,path|{s})
            if not chosen or (value>best if s.turn==1 else value<best): best,chosen=value,(a,)+continuation
            if s.turn==1: alpha=max(alpha,best)
            else: beta=min(beta,best)
            if alpha>=beta: break
        return best,chosen
    legal=rules.actions(state)
    if not legal: return (None,0,0,nodes,None) if include_capture else (None,0,0,nodes)
    best=legal[0]; value=0; completed=0; capture=None
    for depth in range(1,65):
        try:
            score,plan=visit(state,depth,-float('inf'),float('inf'),set())
            if plan:
                best,value,completed=plan[0],score,depth
                capture=plan[1] if len(plan)>1 and plan[1][0]==-2 else None
            if abs(score)>90000: break
        except TimeoutError: break
    return (best,value,completed,nodes,capture) if include_capture else (best,value,completed,nodes)

class App:
    def __init__(self,root):
        self.root=root; root.title('AC3 · Mühle-Assistent'); root.geometry('1030x790')
        root.configure(bg='#14232b')
        self.state=State(); self.history=[]; self.selected=None; self.hint=None; self.version=0; self.busy=False
        self.capture_hint=None
        self.variant=tk.StringVar(value="12er-Mühle")
        self.pending_capture=tk.BooleanVar(value=False)
        self.results=queue.Queue()
        self.diagonal=tk.BooleanVar(value=True); self.flying=tk.BooleanVar(value=True); self.edit=tk.BooleanVar()
        self.paint=tk.IntVar(value=1); self.turn=tk.StringVar(value='Weiß'); self.r1=tk.IntVar(value=12); self.r2=tk.IntVar(value=12)
        main=ttk.Frame(root,padding=18); main.pack(fill='both',expand=True)
        ttk.Label(main,text='AC3 · MÜHLE-ASSISTENT',font=('Segoe UI',22,'bold')).pack(anchor='w')
        variant_row=ttk.Frame(main); variant_row.pack(fill='x',pady=5)
        ttk.Label(variant_row,text='Spielvariante:').pack(side='left',padx=(0,8))
        selector=ttk.Combobox(variant_row,textvariable=self.variant,values=['6er-Mühle','9er-Mühle','12er-Mühle'],state='readonly',width=15)
        selector.pack(side='left'); selector.bind('<<ComboboxSelected>>',self.variant_changed)
        ttk.Label(variant_row,text='  Wechsel startet eine neue Partie.').pack(side='left')
        ttk.Button(variant_row,text='Fanorona öffnen',command=self.open_fanorona).pack(side='right')
        ttk.Label(main,text='AC III • Beide Seiten manuell führen, Empfehlungen ins Spiel übertragen.').pack(anchor='w',pady=(0,12))
        body=ttk.Frame(main); body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,width=650,height=650,bg='#14232b',highlightthickness=0)
        self.canvas.pack(side='left',fill='both',expand=True); self.canvas.bind('<Button-1>',self.click); self.canvas.bind('<Configure>',lambda e:self.draw())
        side=ttk.Frame(body,width=290,padding=(18,0)); side.pack(side='right',fill='y')
        self.status=tk.StringVar(); ttk.Label(side,textvariable=self.status,wraplength=265,font=('Segoe UI',12,'bold')).pack(anchor='w',pady=10)
        ttk.Label(side,text='Rechenzeit pro Empfehlung').pack(anchor='w')
        self.seconds=tk.StringVar(value='5'); ttk.Combobox(side,textvariable=self.seconds,values=['1','5','15','30','60'],state='readonly',width=10).pack(anchor='w',pady=6)
        self.calc=ttk.Button(side,text='Besten Zug berechnen',command=self.calculate); self.calc.pack(fill='x',pady=5)
        self.apply=ttk.Button(side,text='Empfehlung übernehmen',command=self.use_hint,state='disabled'); self.apply.pack(fill='x',pady=5)
        ttk.Button(side,text='Zug zurück',command=self.undo).pack(fill='x',pady=5)
        ttk.Button(side,text='Neues Spiel',command=self.reset).pack(fill='x',pady=5)
        self.info=tk.StringVar(value='Klicke ein freies Feld zum Setzen.\nBeim Ziehen: eigenen Stein, dann Zielfeld.\nNach einer Mühle: gegnerischen Stein anklicken.')
        ttk.Label(side,textvariable=self.info,wraplength=265).pack(anchor='w',pady=14)
        ttk.Separator(side).pack(fill='x',pady=8)
        ttk.Checkbutton(side,text='Stellung bearbeiten',variable=self.edit,command=self.edit_changed).pack(anchor='w')
        for p,name in ((1,'Weiß setzen'),(2,'Schwarz setzen'),(0,'Feld leeren')):
            ttk.Radiobutton(side,text=name,variable=self.paint,value=p).pack(anchor='w')
        ttk.Label(side,text='Noch NICHT gesetzte Steine:').pack(anchor='w',pady=(8,0))
        self.reserve_inputs=[]
        for name,var in (('Weiß',self.r1),('Schwarz',self.r2)):
            row=ttk.Frame(side); row.pack(fill='x'); ttk.Label(row,text=name,width=10).pack(side='left')
            spin=ttk.Spinbox(row,from_=0,to=12,textvariable=var,width=5); spin.pack(side='left'); self.reserve_inputs.append(spin)
        ttk.Label(side,text='Am Zug:').pack(anchor='w',pady=(6,0))
        ttk.Combobox(side,textvariable=self.turn,values=['Weiß','Schwarz'],state='readonly',width=12).pack(anchor='w')
        ttk.Checkbutton(side,text='Am Zug muss noch einen Stein nehmen',variable=self.pending_capture).pack(anchor='w')
        ttk.Button(side,text='Stellung anwenden',command=self.commit).pack(fill='x',pady=6)
        self.diagonal_control=ttk.Checkbutton(side,text='Diagonale Mühlen (12er)',variable=self.diagonal,command=self.rule_changed)
        self.diagonal_control.pack(anchor='w')
        ttk.Checkbutton(side,text='Springen mit 3 Steinen',variable=self.flying,command=self.rule_changed).pack(anchor='w')
        ttk.Label(side,text='Such-KI, keine garantierte perfekte Lösung.\nWeiß und Schwarz beziehen sich auf dieses Brett.',wraplength=265).pack(anchor='w',pady=10)
        self.refresh(); self.timer=root.after(100,self.poll)
        root.bind('<Destroy>',self.destroyed,add='+')

    def destroyed(self,event):
        if event.widget==self.root:
            try: self.root.after_cancel(self.timer)
            except tk.TclError: pass

    def open_fanorona(self):
        from fanorona import FanoronaApp
        window=getattr(self,'fanorona_window',None)
        if window is not None and window.winfo_exists():
            window.deiconify(); window.lift(); return
        self.fanorona_window=tk.Toplevel(self.root)
        self.fanorona_app=FanoronaApp(self.fanorona_window)

    def rules(self): return Rules(self.diagonal.get(),self.flying.get(),int(self.variant.get().split('er')[0]))
    def variant_changed(self,event=None):
        variant=int(self.variant.get().split('er')[0])
        self.diagonal.set(variant==12)
        # AC3 permits flying with three remaining pieces, including Six Men's Morris.
        self.flying.set(True)
        self.diagonal_control.configure(state='normal' if variant==12 else 'disabled')
        for spin in self.reserve_inputs: spin.configure(to=variant)
        self.reset()
    def invalidate(self):
        self.version+=1; self.hint=None; self.capture_hint=None; self.selected=None; self.apply.configure(state='disabled')
    def refresh(self):
        s=self.state; name=['','Weiß','Schwarz'][s.turn]; winner=self.rules().terminal(s)
        text=('Remis: Brett voll.' if winner==0 else f'{["","Weiß","Schwarz"][winner]} gewinnt.') if winner is not None else f'{name}: '+('Stein schlagen' if s.capture else ('Stein setzen' if s.reserve[s.turn-1] else 'Stein ziehen'))
        self.status.set(text+f'\nVorrat W / S: {s.reserve[0]} / {s.reserve[1]}\nBrett W / S: {s.board.count(1)} / {s.board.count(2)}')
        self.pending_capture.set(s.capture)
        self.r1.set(s.reserve[0]); self.r2.set(s.reserve[1]); self.turn.set(name); self.draw()
    def coords(self,i):
        size=min(self.canvas.winfo_width(),self.canvas.winfo_height())-85; x,y=POINTS[i]
        return 42+x*size/6,42+y*size/6
    def draw(self):
        c=self.canvas; c.delete('all')
        for line in self.rules().lines:
            for a,b in zip(line,line[1:]): c.create_line(*self.coords(a),*self.coords(b),fill='#a78652',width=3)
        removable={a[1] for a in self.rules().actions(self.state)} if self.state.capture else set()
        for i in self.rules().points:
            v=self.state.board[i]
            x,y=self.coords(i); color=['#36515d','#f3e9cf','#1c1b22'][v]
            outline='#56dbc1' if self.hint and i in self.hint else ('#f4b85d' if i==self.selected else '#a78652')
            c.create_oval(x-14,y-14,x+14,y+14,fill=color,outline=outline,width=4 if i==self.selected or (self.hint and i in self.hint) else 2)
            if i in removable:
                c.create_oval(x-18,y-18,x+18,y+18,outline='#ff9895',width=2)
            c.create_text(x+19,y-19,text=NAMES[i],fill='#c1d1d5',font=('Segoe UI',10))
        target = self.capture_hint[1] if self.capture_hint else (self.hint[1] if self.hint and self.hint[0]==-2 else None)
        if target is not None:
            x,y=self.coords(target)
            c.create_oval(x-21,y-21,x+21,y+21,outline='#ff706c',width=4)
            c.create_text(x,y+34,text='NEHMEN',fill='#ff9895',font=('Segoe UI',10,'bold'))
        if self.hint and self.hint[0]>=0:
            c.create_line(*self.coords(self.hint[0]),*self.coords(self.hint[1]),fill='#56dbc1',width=4,arrow='last')
    def click(self,e):
        i=min(self.rules().points,key=lambda j:(self.coords(j)[0]-e.x)**2+(self.coords(j)[1]-e.y)**2)
        x,y=self.coords(i)
        if (x-e.x)**2+(y-e.y)**2>650: return
        if self.edit.get():
            b=list(self.state.board); b[i]=self.paint.get(); self.state=State(tuple(b),self.state.reserve,self.state.turn); self.invalidate(); self.draw(); return
        r=self.rules()
        # The red capture target may already be shown before the mill move
        # has been transferred to this board. A click completes both steps.
        if not self.state.capture and self.capture_hint == (-2,i) and self.hint in r.actions(self.state):
            self.use_hint()
        legal=r.actions(self.state)
        if self.state.capture: a=(-2,i)
        elif self.state.reserve[self.state.turn-1]: a=(-1,i)
        else:
            if self.state.board[i]==self.state.turn: self.selected=i; self.draw(); return
            a=(self.selected,i)
        if a in legal:
            self.move(a)
        elif self.state.capture:
            self.info.set('Diesen Stein kannst du nicht nehmen. Klicke einen rosa umrandeten gegnerischen Stein. Mühlen sind geschützt, solange andere Steine frei stehen.')
        elif self.state.board[i]==3-self.state.turn:
            self.info.set('Steine nehmen geht nach einer neu gebildeten Mühle. Bei übernommener Stellung: „Am Zug muss noch einen Stein nehmen“ aktivieren und „Stellung anwenden“ klicken.')
    def move(self,a):
        self.history.append(self.state); self.state=self.rules().play(self.state,a); self.invalidate(); self.refresh()
        if self.state.capture:
            self.info.set('Mühle! Bester gegnerischer Stein wird berechnet …')
            self.calculate()
    def undo(self):
        if self.history: self.state=self.history.pop(); self.invalidate(); self.refresh()
    def reset(self):
        self.state=self.rules().initial(); self.history=[]; self.edit.set(False); self.invalidate(); self.refresh(); self.info.set(f'{self.variant.get()}: Neues Spiel. Weiß beginnt. Bei Bedarf im Stellungseditor Schwarz als Startspieler wählen.')
    def edit_changed(self): self.invalidate(); self.draw()
    def rule_changed(self): self.invalidate(); self.refresh()
    def commit(self):
        try:
            r=(self.r1.get(),self.r2.get())
            limit=self.rules().variant
            if any(n<0 or n>limit or n+self.state.board.count(p)>limit for p,n in enumerate(r,1)): raise ValueError
        except (ValueError,tk.TclError): messagebox.showerror('Ungültige Stellung',f'Brettsteine plus Vorrat dürfen je Farbe höchstens {self.rules().variant} sein.'); return
        self.history.append(self.state); self.state=State(self.state.board,r,1 if self.turn.get()=='Weiß' else 2,self.pending_capture.get())
        self.edit.set(False); self.invalidate(); self.refresh()
        if self.state.capture:
            self.info.set('Jetzt einen rosa umrandeten gegnerischen Stein nehmen oder den besten Schlag berechnen lassen.')
    def describe(self,a):
        src,dst=a
        return f'Schlage {NAMES[dst]}.' if src==-2 else (f'Setze auf {NAMES[dst]}.' if src==-1 else f'Ziehe {NAMES[src]} → {NAMES[dst]}.')
    def calculate(self):
        if self.busy or self.edit.get(): return
        if self.rules().terminal(self.state) is not None: return
        self.busy=True; self.calc.configure(state='disabled'); self.info.set('Berechnung läuft …')
        version=self.version; state=self.state; rules=self.rules(); seconds=float(self.seconds.get())
        def worker():
            try: result=search(rules,state,seconds,include_capture=True)
            except Exception as exc: result=exc
            self.results.put((version,result))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            version,result=self.results.get_nowait(); self.busy=False; self.calc.configure(state='normal')
            if version==self.version:
                if isinstance(result,Exception): self.info.set(f'Berechnung fehlgeschlagen: {result}')
                else:
                    a,value,depth,nodes,capture=result; self.hint=a; self.capture_hint=capture
                    self.info.set((self.describe(a) if a else 'Kein legaler Zug.')+(f'\nMühle! Nimm danach den gegnerischen Stein auf {NAMES[capture[1]]} (rot markiert).' if capture else '')+f'\nSuchtiefe: {depth} Halbzüge\nUntersuchte Stellungen: {nodes:,}')
                    self.apply.configure(state='normal' if a else 'disabled'); self.draw()
            else: self.info.set('Stellung geändert. Bitte erneut berechnen.')
        except queue.Empty: pass
        self.timer=self.root.after(100,self.poll)
    def use_hint(self):
        if self.hint in self.rules().actions(self.state):
            a,capture=self.hint,self.capture_hint
            # Use the capture from the same completed search without a second wait.
            if capture and self.rules().play(self.state,a).capture:
                self.history.append(self.state)
                self.state=self.rules().play(self.state,a)
                self.invalidate(); self.hint=capture
                self.info.set('Mühle! '+self.describe(capture)+'\nDer zu nehmende Stein ist rot markiert.')
                self.apply.configure(state='normal'); self.refresh()
            else:
                self.move(a)

if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
