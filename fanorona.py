"""Fanorona 9x5: rules, timed search and a desktop companion."""
from dataclasses import dataclass
import time
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue

POINTS = tuple((x,y) for y in range(5) for x in range(9))
NAMES = tuple(f'{"abcdefghi"[x]}{5-y}' for x,y in POINTS)
STOP = (-1,-1,'stop')

@dataclass(frozen=True)
class FanoronaState:
    board: tuple
    turn: int = 1
    active: int = -1
    visited: tuple = ()
    direction: tuple = ()

class FanoronaRules:
    def __init__(self, must_continue=False):
        self.must_continue=must_continue
        self.adj=[]
        for x,y in POINTS:
            directions=[(1,0),(-1,0),(0,1),(0,-1)]
            if (x+y)%2==0: directions += [(1,1),(1,-1),(-1,1),(-1,-1)]
            self.adj.append(tuple((y+dy)*9+x+dx for dx,dy in directions
                                  if 0<=x+dx<9 and 0<=y+dy<5))
        self.edges=tuple((i,j) for i,ns in enumerate(self.adj) for j in ns if i<j)

    def initial(self):
        return FanoronaState((2,)*18+(2,1,2,1,0,2,1,2,1)+(1,)*18)

    def captured(self,s,a):
        src,dst,mode=a
        if mode not in ('A','W'): return ()
        x,y=POINTS[src]; tx,ty=POINTS[dst]; dx,dy=tx-x,ty-y
        if mode=='A': x,y=tx+dx,ty+dy
        else: x,y=x-dx,y-dy; dx,dy=-dx,-dy
        result=[]
        while 0<=x<9 and 0<=y<5 and s.board[y*9+x]==3-s.turn:
            result.append(y*9+x); x+=dx; y+=dy
        return tuple(result)

    def captures(self,s):
        result=[]
        pieces=(s.active,) if s.active>=0 else range(45)
        for i in pieces:
            if s.board[i]!=s.turn: continue
            x,y=POINTS[i]
            for j in self.adj[i]:
                dx,dy=POINTS[j][0]-x,POINTS[j][1]-y
                if s.board[j] or j in s.visited or (dx,dy)==s.direction: continue
                for mode in ('A','W'):
                    a=(i,j,mode)
                    if self.captured(s,a): result.append(a)
        return result

    def actions(self,s):
        moves=self.captures(s)
        if s.active>=0:
            return moves+([STOP] if not self.must_continue or not moves else [])
        if moves: return moves
        return [(i,j,'P') for i in range(45) if s.board[i]==s.turn
                for j in self.adj[i] if not s.board[j]]

    def play(self,s,a):
        if a==STOP: return FanoronaState(s.board,3-s.turn)
        src,dst,mode=a; b=list(s.board); b[src]=0; b[dst]=s.turn
        for i in self.captured(s,a): b[i]=0
        if mode=='P' or 3-s.turn not in b: return FanoronaState(tuple(b),3-s.turn)
        direction=(POINTS[dst][0]-POINTS[src][0],POINTS[dst][1]-POINTS[src][1])
        t=FanoronaState(tuple(b),s.turn,dst,(s.visited or (src,))+(dst,),direction)
        return t if self.captures(t) else FanoronaState(tuple(b),3-s.turn)

    def terminal(self,s):
        if 1 not in s.board: return 2
        if 2 not in s.board: return 1
        if not self.actions(s): return 3-s.turn
        return None

    def evaluate(self,s):
        value=150*(s.board.count(1)-s.board.count(2))
        for i,v in enumerate(s.board):
            if v:
                x,y=POINTS[i]
                value+=(1 if v==1 else -1)*(8-abs(x-4)-abs(y-2)+sum(not s.board[j] for j in self.adj[i]))
        return value


def search_fanorona(rules,state,seconds):
    deadline=time.monotonic()+seconds; nodes=0
    legal=rules.actions(state)
    if rules.terminal(state) is not None: return (),0,0,0
    # A legal fallback is available even when the time budget is tiny.
    best=(max(legal,key=lambda a:len(rules.captured(state,a))),)
    completed=0; value=0
    def visit(s,depth,alpha,beta,path):
        nonlocal nodes
        nodes+=1
        if time.monotonic()>=deadline: raise TimeoutError
        winner=rules.terminal(s)
        if winner is not None: return (100000+depth if winner==1 else -100000-depth),()
        if s in path: return 0,()
        if depth<=0 and s.active<0: return rules.evaluate(s),()
        moves=rules.actions(s)
        moves.sort(key=lambda a:len(rules.captured(s,a)),reverse=True)
        score=-float('inf') if s.turn==1 else float('inf'); plan=()
        for a in moves:
            child=rules.play(s,a)
            v,pv=visit(child,depth-int(child.turn!=s.turn),alpha,beta,path|{s})
            if not plan or (v>score if s.turn==1 else v<score): score,plan=v,(a,)+pv
            if s.turn==1: alpha=max(alpha,score)
            else: beta=min(beta,score)
            if alpha>=beta: break
        return score,plan
    for depth in range(1,50):
        try:
            score,plan=visit(state,depth,-float('inf'),float('inf'),set())
            if plan:
                # Show only this player's complete turn, not the opponent's reply.
                t=state; turn_plan=[]
                for a in plan:
                    turn_plan.append(a); t=rules.play(t,a)
                    if t.turn!=state.turn: break
                best=tuple(turn_plan); value=score; completed=depth
            if abs(score)>90000: break
        except TimeoutError: break
    return best,value,completed,nodes

class FanoronaApp:
    def __init__(self,root,back_to_menu=None):
        self.root=root; root.title('AC3 · Fanorona-Assistent'); root.geometry('1120x900')
        self.state=FanoronaRules().initial(); self.history=[]; self.selected=None; self.plan=()
        self.version=0; self.busy=False; self.results=queue.Queue()
        self.edit=tk.BooleanVar(value=False); self.paint=tk.IntVar(value=1)
        self.turn=tk.StringVar(value='Weiß'); self.seconds=tk.StringVar(value='5')
        self.must_continue=tk.BooleanVar(value=False); self.choice=()
        frame=ttk.Frame(root,padding=16); frame.pack(fill='both',expand=True)
        header=ttk.Frame(frame); header.pack(fill='x')
        ttk.Label(header,text='AC3 · FANORONA',font=('Segoe UI',22,'bold')).pack(side='left')
        if back_to_menu is not None:
            ttk.Button(header,text='← Hauptmenü',command=back_to_menu).pack(side='right')
        ttk.Label(frame,text='Eigener Stein → freies Nachbarfeld → bei Bedarf Schlagart wählen. Rot = entfernte Gegnersteine.').pack(anchor='w',pady=8)
        body=ttk.Frame(frame); body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,bg='#14232b',highlightthickness=0,width=740,height=610)
        self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.draw()); self.canvas.bind('<Button-1>',self.click)
        side=ttk.Frame(body,padding=(14,0)); side.pack(side='right',fill='y')
        self.status=tk.StringVar(); ttk.Label(side,textvariable=self.status,font=('Segoe UI',12,'bold'),wraplength=290).pack(anchor='w',pady=8)
        ttk.Label(side,text='Rechenzeit (Sekunden)').pack(anchor='w')
        ttk.Combobox(side,textvariable=self.seconds,values=['1','5','15','30','60'],width=10,state='readonly').pack(anchor='w',pady=5)
        self.calc=ttk.Button(side,text='Besten Zug / Schlagkette berechnen',command=self.calculate); self.calc.pack(fill='x',pady=4)
        self.apply=ttk.Button(side,text='Nächsten empfohlenen Schritt übernehmen',command=self.use_hint); self.apply.pack(fill='x',pady=4)
        self.stop=ttk.Button(side,text='Schlagkette beenden',command=lambda:self.move(STOP)); self.stop.pack(fill='x',pady=4)
        self.approach=ttk.Button(side,text='Annäherung: Gegner vor dem Ziel',command=lambda:self.choose('A')); self.approach.pack(fill='x',pady=4)
        self.withdraw=ttk.Button(side,text='Rückzug: Gegner hinter dem Start',command=lambda:self.choose('W')); self.withdraw.pack(fill='x',pady=4)
        ttk.Button(side,text='Schritt zurück',command=self.undo).pack(fill='x',pady=4)
        ttk.Button(side,text='Neues Spiel',command=self.reset).pack(fill='x',pady=4)
        self.info=tk.StringVar(value='Weiß beginnt. Schlagen ist Pflicht, wenn ein Schlag möglich ist.')
        from tkinter.scrolledtext import ScrolledText
        self.details=ScrolledText(side,width=40,height=6,wrap='word',font=('Segoe UI',9),state='disabled')
        self.details.pack(fill='x',pady=10)
        def update_details(*_):
            self.details.configure(state='normal'); self.details.delete('1.0','end')
            self.details.insert('1.0',self.info.get()); self.details.configure(state='disabled')
        self.info.trace_add('write',update_details); update_details()
        ttk.Separator(side).pack(fill='x',pady=8)
        ttk.Checkbutton(side,text='Stellung bearbeiten',variable=self.edit,command=self.edit_changed).pack(anchor='w')
        for p,name in ((1,'Weiß setzen'),(2,'Schwarz setzen'),(0,'Feld leeren')):
            ttk.Radiobutton(side,text=name,variable=self.paint,value=p).pack(anchor='w')
        ttk.Label(side,text='Am Zug:').pack(anchor='w')
        ttk.Combobox(side,textvariable=self.turn,values=['Weiß','Schwarz'],state='readonly',width=12).pack(anchor='w',pady=4)
        ttk.Button(side,text='Stellung als neuen Zug anwenden',command=self.commit).pack(fill='x',pady=4)
        ttk.Checkbutton(side,text='Schlagkette muss fortgesetzt werden',variable=self.must_continue,command=self.rules_changed).pack(anchor='w')
        ttk.Label(side,text='Ohne Haken: freiwilliges Kettenende.\nSuch-KI ohne Gewinngarantie.',wraplength=290).pack(anchor='w',pady=6)
        self.refresh(); self.timer=root.after(100,self.poll)
        root.bind('<Destroy>',self.destroyed,add='+')

    def destroyed(self,event):
        if event.widget==self.root:
            try: self.root.after_cancel(self.timer)
            except tk.TclError: pass

    def rules(self): return FanoronaRules(self.must_continue.get())
    def invalidate(self):
        self.version+=1; self.plan=(); self.choice=(); self.selected=None
    def coords(self,i):
        w=max(180,self.canvas.winfo_width()); h=max(180,self.canvas.winfo_height())
        step=min((w-80)/8,(h-80)/4); x,y=POINTS[i]
        return (w-8*step)/2+x*step,(h-4*step)/2+y*step
    def refresh(self):
        s=self.state; winner=self.rules().terminal(s); name=('Weiß' if s.turn==1 else 'Schwarz')
        self.status.set((f'{"Weiß" if winner==1 else "Schwarz"} gewinnt.' if winner else
                         name+(': Schlagkette fortsetzen' if s.active>=0 else ': am Zug'))+
                        f'\nSteine W / S: {s.board.count(1)} / {s.board.count(2)}')
        self.turn.set(name)
        self.apply.configure(state='normal' if self.plan and not self.edit.get() else 'disabled')
        self.stop.configure(state='normal' if s.active>=0 and STOP in self.rules().actions(s) and not self.edit.get() else 'disabled')
        for button in (self.approach,self.withdraw): button.configure(state='normal' if self.choice else 'disabled')
        self.draw()
    def draw(self):
        c=self.canvas; c.delete('all'); rules=self.rules()
        for i,j in rules.edges: c.create_line(*self.coords(i),*self.coords(j),fill='#a78652',width=2)
        legal=rules.actions(self.state) if rules.terminal(self.state) is None else []
        targets={a[1] for a in legal if a!=STOP and a[0]==self.selected}
        captured=rules.captured(self.state,self.plan[0]) if self.plan else ()
        for i,v in enumerate(self.state.board):
            x,y=self.coords(i); outline='#ff706c' if i in captured else ('#56dbc1' if i in targets else '#a78652')
            if i==self.selected or i==self.state.active: outline='#f4b85d'
            c.create_oval(x-12,y-12,x+12,y+12,fill=('#36515d','#f3e9cf','#1c1b22')[v],outline=outline,width=3)
            c.create_text(x+13,y-18,text=NAMES[i],fill='#c1d1d5',font=('Segoe UI',9))
            if i in captured: c.create_text(x,y,text='×',fill='#ff706c',font=('Segoe UI',19,'bold'))
        if self.plan and self.plan[0]!=STOP:
            a=self.plan[0]; c.create_line(*self.coords(a[0]),*self.coords(a[1]),fill='#56dbc1',width=4,arrow='last')
    def click(self,event):
        i=min(range(45),key=lambda j:(self.coords(j)[0]-event.x)**2+(self.coords(j)[1]-event.y)**2)
        x,y=self.coords(i)
        if (x-event.x)**2+(y-event.y)**2>500: return
        if self.edit.get():
            b=list(self.state.board); b[i]=self.paint.get()
            self.state=FanoronaState(tuple(b),self.state.turn); self.invalidate(); self.refresh(); return
        if self.rules().terminal(self.state) is not None: return
        if self.state.board[i]==self.state.turn:
            if self.state.active>=0 and i!=self.state.active:
                self.info.set('In einer Schlagkette muss derselbe Stein weiterziehen.'); return
            self.selected=i; self.choice=(); self.refresh(); return
        source=self.state.active if self.state.active>=0 else self.selected
        options=[a for a in self.rules().actions(self.state) if a!=STOP and a[:2]==(source,i)]
        if len(options)==1: self.move(options[0])
        elif len(options)==2:
            self.choice=tuple(options); self.info.set('Beide Schlagarten sind möglich. Wähle Annäherung oder Rückzug.'); self.refresh()
        else: self.info.set('Kein erlaubter Zug. Grün zeigt mögliche Ziele; vorhandene Schläge haben Vorrang.')
    def choose(self,mode):
        a=next((a for a in self.choice if a[2]==mode),None)
        if a: self.move(a)
    def describe(self,a,s):
        if a==STOP: return 'Schlagkette beenden.'
        mode={'A':'Annäherung','W':'Rückzug','P':'ohne Schlag'}[a[2]]
        victims=self.rules().captured(s,a)
        return f'{NAMES[a[0]]} → {NAMES[a[1]]}: {mode}'+(' · nimm '+', '.join(NAMES[i] for i in victims) if victims else '')
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
        self.info.set(description+('\nKette fortsetzen oder beenden.' if self.state.active>=0 else ''))
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
        self.info.set('Neue Partie: Weiß beginnt.'); self.refresh()
    def edit_changed(self):
        if self.edit.get() and self.state.active>=0:
            self.history.append(self.state); self.state=FanoronaState(self.state.board,self.state.turn)
        self.invalidate(); self.info.set('Editor: Stellung zu Beginn eines Zuges eintragen. Laufende Schlagketten bitte mit Schritt zurück rekonstruieren.'); self.refresh()
    def commit(self):
        if any(self.state.board.count(p)>22 for p in (1,2)) or not all(p in self.state.board for p in (1,2)):
            messagebox.showerror('Ungültige Stellung','Je Farbe 1 bis 22 Steine eintragen.',parent=self.root); return
        self.history.append(self.state); self.state=FanoronaState(self.state.board,1 if self.turn.get()=='Weiß' else 2)
        self.edit.set(False); self.invalidate(); self.info.set('Stellung übernommen: Beginn eines neuen Zuges.'); self.refresh()
    def rules_changed(self): self.invalidate(); self.info.set('Kettenregel geändert. Bitte neu berechnen.'); self.refresh()
    def calculate(self):
        if self.busy or self.edit.get() or self.rules().terminal(self.state) is not None: return
        self.busy=True; self.calc.configure(state='disabled'); self.info.set('Zug und Schlagkette werden berechnet …')
        version=self.version; state=self.state; rules=self.rules(); seconds=float(self.seconds.get())
        def work():
            try: result=search_fanorona(rules,state,seconds)
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
    root=tk.Tk(); FanoronaApp(root); root.mainloop()
