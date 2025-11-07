import json
import os
import random
import math
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

SAVE_SLOTS = ["city_save_slot1.json", "city_save_slot2.json", "city_save_slot3.json"]
LEGACY_TXT = "city_save.txt"
AUTO_DAY_INTERVAL_MS = 2000
MARKET_BASE = {"wood": 10, "stone": 12}
BUY_SPREAD = 1.25
SELL_SPREAD = 0.9

PRESTIGE_MONEY_REQ = 10_000_000
PRESTIGE_POP_REQ = 1000

FONT_MAIN = ("Segoe UI", 10)
FONT_BIG = ("Segoe UI", 11, 'bold')


class CityGame:
    def __init__(self):
        # podstawowe
        self.playername = "MojeMiasto"
        self.day = 1
        self.money = 500
        self.population = 10
        self.happiness = 50
        self.wood = 50
        self.stone = 20
        # menadzer
        self.manager = "Brak"
        self.manager_bonus = 0
        # budynki
        self.buildings = {"house": 0, "pavilion": 0, "workshop": 0, "market": 0, "farm": 0, "sawmill": 0, "quarry": 0, "school": 0, "hospital": 0}
        self.production = {"workshop": 10, "farm": 8, "sawmill": 6, "quarry": 4}
        # badania i ulepszenia
        self.research_points = 0
        self.upgrades = {"better_tools": False, "market_reforms": False, 'reduced_build_costs': False, 'manager_prod': False}
        self.achievements = set()
        # quests
        self.quests = {}
        self.init_default_quests()
        # prestige
        self.prestige_points = 0
        # internal flags
        self.normalize()

    def init_default_quests(self):
        self.quests = {
            'q_pop100': {"desc": "Osiągnij populację 100", "done": False, "reward": {"money": 5000}},
            'q_money50k': {"desc": "Zdobądź 50 000 pieniędzy", "done": False, "reward": {"research": 50}},
            'q_build_farm_10': {"desc": "Wybuduj 10 farm", "done": False, "reward": {"money": 2000, "research": 10}},
        }

    def to_dict(self):
        return {
            "playername": self.playername,
            "day": self.day,
            "money": self.money,
            "population": self.population,
            "happiness": self.happiness,
            "wood": self.wood,
            "stone": self.stone,
            "manager": self.manager,
            "manager_bonus": self.manager_bonus,
            "buildings": self.buildings,
            "production": self.production,
            "research_points": self.research_points,
            "upgrades": self.upgrades,
            "achievements": list(self.achievements),
            "quests": self.quests,
            "prestige_points": self.prestige_points,
        }

    def from_dict(self, data: dict):
        self.playername = data.get("playername", self.playername)
        self.day = int(data.get("day", self.day))
        self.money = int(data.get("money", self.money))
        self.population = int(data.get("population", self.population))
        self.happiness = int(data.get("happiness", self.happiness))
        self.wood = int(data.get("wood", self.wood))
        self.stone = int(data.get("stone", self.stone))
        self.manager = data.get("manager", self.manager)
        self.manager_bonus = int(data.get("manager_bonus", self.manager_bonus)) if 'manager_bonus' in data else 0
        self.buildings.update(data.get("buildings", {}))
        self.production.update(data.get("production", {}))
        self.research_points = int(data.get("research_points", self.research_points))
        self.upgrades.update(data.get("upgrades", {}))
        self.achievements = set(data.get("achievements", []))
        if 'quests' in data:
            self.quests.update(data.get('quests'))
        self.prestige_points = int(data.get('prestige_points', self.prestige_points))
        self.normalize()

    def normalize(self):
        self.wood = max(0, int(self.wood))
        self.stone = max(0, int(self.stone))
        self.happiness = max(0, min(100, int(self.happiness)))
        self.population = max(0, int(self.population))
        self.money = max(0, int(self.money))

    def save(self, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            return True, f'Zapisano do {filename}'
        except Exception as e:
            return False, str(e)

    def load(self, filename):
        try:
            if not os.path.exists(filename):
                return False, 'Plik zapisu nie istnieje.'
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.from_dict(data)
            return True, 'Wczytano zapis.'
        except Exception as e:
            return False, str(e)

    def import_legacy_txt(self, filename=LEGACY_TXT):
        try:
            if not os.path.exists(filename):
                return False, 'Brak legacy pliku.'
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' not in line: continue
                    key, val = line.split('=', 1); key=key.strip(); val=val.strip()
                    if key == 'playername': self.playername = val
                    elif key == 'day': self.day = int(val)
                    elif key == 'money': self.money = int(val)
                    elif key == 'population': self.population = int(val)
                    elif key == 'happiness': self.happiness = int(val)
                    elif key == 'wood': self.wood = int(val)
                    elif key == 'stone': self.stone = int(val)
                    elif key == 'manager': self.manager = val
                    elif key == 'workshop': self.buildings['workshop'] = int(val)
            self.normalize()
            return True, 'Zaimportowano legacy zapis.'
        except Exception as e:
            return False, str(e)

    # oblicz efektywną liczbę budynków (diminishing returns)
    def effective_count(self, cnt):
        if cnt <= 0: return 0
        return int(max(1, math.pow(cnt, 0.85)))

    def production_day(self):
        total_money = 0
        total_wood = 0
        total_stone = 0
        # multiplier z prestiżu
        prestige_mult = 1.0 + (self.prestige_points * 0.02)
        # lepsze narzędzia
        tool_mult = 1.2 if self.upgrades.get('better_tools') else 1.0
        # manager production bonus (ograniczony)
        mgr_prod_bonus = 0.15 if self.upgrades.get('manager_prod') else 0.0
        mgr_prod_bonus = min(mgr_prod_bonus, 0.5)
        for b, cnt in self.buildings.items():
            if cnt <= 0: continue
            eff = self.effective_count(cnt)
            if b == 'workshop':
                base = int(self.production['workshop'] * eff)
                total_money += int(base * tool_mult * (1 + mgr_prod_bonus))
            elif b == 'farm':
                base = int(self.production['farm'] * eff)
                total_money += int(base * tool_mult * (1 + mgr_prod_bonus))
            elif b == 'sawmill':
                base = int(self.production['sawmill'] * eff)
                total_wood += int(base * tool_mult)
            elif b == 'quarry':
                base = int(self.production['quarry'] * eff)
                total_stone += int(base * tool_mult)
            elif b == 'market':
                total_money += int(2 * eff)
        # podstawowy dochód z populacji
        base_income = (self.population * self.happiness) // 30
        total_money += base_income
        # menadzer procentowy teraz tylko na base_income (ograniczenie exploitów)
        if self.manager_bonus:
            total_money += (base_income * self.manager_bonus) // 100
        # zastosuj prestiżowy mnożnik dopiero na produkcję (ale nie na koszty/handel)
        total_money = int(total_money * prestige_mult)
        total_wood = int(total_wood * prestige_mult)
        total_stone = int(total_stone * prestige_mult)

        self.money += total_money
        self.wood += total_wood
        self.stone += total_stone
        # drobne efekty budynków
        self.happiness += self.buildings.get('pavilion', 0) * 1
        self.happiness += self.buildings.get('hospital', 0) * 1
        self.happiness += self.buildings.get('school', 0) * 1
        # badania z schools
        self.research_points += int(self.buildings.get('school', 0) * 0.5 * prestige_mult)
        self.normalize()
        return {'money': total_money, 'wood': total_wood, 'stone': total_stone}

    def end_day(self):
        produced = self.production_day()
        r = random.randint(0, 99)
        event_text = 'Dzień spokojny.'
        if r < 6:
            lost = min(20, self.wood); self.wood -= lost; self.happiness -= 6
            event_text = f'Pożar! Straciłeś {lost} drewna i -6 szczęścia.'
        elif r < 14:
            self.money += 50; self.wood += 15; event_text = 'Dobry rok: +50$, +15 drewna.'
        elif r < 22:
            self.population += 5; self.happiness += 3; event_text = 'Migracja: +5 osób.'
        elif r < 26:
            lost_money = min(100, self.money); self.money -= lost_money; self.happiness -= 10
            event_text = f'Skandal: straciłeś {lost_money}$ i -10 szczęścia.'
        self.day += 1
        self.check_achievements(); self.check_quests()
        return produced, event_text

    def check_achievements(self):
        if self.money >= 10000: self.achievements.add('Wealthy')
        if self.population >= 100: self.achievements.add('Pop100')
        if self.day >= 365: self.achievements.add('YearSurvivor')

    def check_quests(self):
        for qid, q in self.quests.items():
            if q.get('done'): continue
            if qid == 'q_pop100' and self.population >= 100:
                q['done'] = True; self.apply_reward(q['reward'])
            if qid == 'q_money50k' and self.money >= 50000:
                q['done'] = True; self.apply_reward(q['reward'])
            if qid == 'q_build_farm_10' and self.buildings.get('farm', 0) >= 10:
                q['done'] = True; self.apply_reward(q['reward'])

    def apply_reward(self, reward: dict):
        if not reward: return
        self.money += reward.get('money', 0)
        self.research_points += reward.get('research', 0)
        self.wood += reward.get('wood', 0)
        self.stone += reward.get('stone', 0)

    # prestiż: oblicz ile punktów dałby reset teraz
    def prestige_value_if_reset(self):
        pts = (self.money // PRESTIGE_MONEY_REQ) + (self.population // PRESTIGE_POP_REQ) + (self.day // 1000)
        return int(pts)

    def can_prestige(self):
        return self.prestige_value_if_reset() > 0

    def do_prestige(self):
        pts = self.prestige_value_if_reset()
        if pts <= 0: return False, 'Za mało postępu by zdobyć prestiż.'
        # nadawaj punkty i resetuj większość rzeczy
        self.prestige_points += pts
        # zachowaj imię, prestiż i ewentualnie pewne kosmetyki — resetujemy rozbudowę
        self.day = 1
        self.money = 1000
        self.population = 10
        self.happiness = 50
        self.wood = 20
        self.stone = 10
        # reset budynków i ulepszeń (możemy zachować niektóre trwałe ulepszenia w przyszłości)
        for k in list(self.buildings.keys()): self.buildings[k] = 0
        # nie usuwamy questów — można ponownie zdobywać nagrody
        # nagradzamy gracza krótkim komunikatem
        return True, f'Zdobyto {pts} punktów prestiżu. Teraz masz {self.prestige_points} punktów.'


class CityGUI(tk.Tk):
    def __init__(self, game: CityGame):
        super().__init__()
        self.title('City - Prestige & Progression')
        self.geometry('1020x560')
        self.resizable(False, False)
        self.game = game
        self.auto_day = False; self.auto_after_id = None; self.auto_interval = AUTO_DAY_INTERVAL_MS
        self.create_widgets(); self.refresh_all()
        self.protocol("WM_DELETE_WINDOW", self.on_quit)
        if os.path.exists(LEGACY_TXT):
            root = tk.Tk(); root.withdraw()
            if messagebox.askyesno('Import','Znaleziono city_save.txt. Zaimportować?'):
                ok,msg = game.import_legacy_txt();
                if ok: game.save(SAVE_SLOTS[0]); messagebox.showinfo('Import','Zaimportowano do slot1')
            root.destroy()

    def create_widgets(self):
        style = ttk.Style(self)
        try: style.theme_use('clam')
        except: pass
        style.configure('.', font=FONT_MAIN)

        # statystyki
        stats = ttk.LabelFrame(self, text='Statystyki', padding=10)
        stats.place(x=10, y=10, width=320, height=260)
        self.lbl_city = ttk.Label(stats, text='', font=FONT_BIG); self.lbl_city.pack(anchor='w')
        self.lbl_day = ttk.Label(stats, text=''); self.lbl_day.pack(anchor='w')
        self.lbl_money = ttk.Label(stats, text=''); self.lbl_money.pack(anchor='w')
        self.lbl_pop = ttk.Label(stats, text=''); self.lbl_pop.pack(anchor='w')
        self.lbl_happy = ttk.Label(stats, text=''); self.lbl_happy.pack(anchor='w')
        self.lbl_wood = ttk.Label(stats, text=''); self.lbl_wood.pack(anchor='w')
        self.lbl_stone = ttk.Label(stats, text=''); self.lbl_stone.pack(anchor='w')
        self.lbl_manager = ttk.Label(stats, text=''); self.lbl_manager.pack(anchor='w')
        self.lbl_research = ttk.Label(stats, text=''); self.lbl_research.pack(anchor='w')
        # prestige info
        self.lbl_prestige = ttk.Label(stats, text='Prestige: 0 pts'); self.lbl_prestige.pack(anchor='w', pady=(6,0))
        self.prestige_bar = ttk.Progressbar(stats, length=280)
        self.prestige_bar.pack(anchor='w', pady=(2,0))

        # budynki
        build_frame = ttk.LabelFrame(self, text='Budynki / Handel', padding=8)
        build_frame.place(x=340, y=10, width=420, height=520)
        row = 0; self.build_buttons = {}
        building_infos = [
            ('house','Dom (+pop)'),('pavilion','Altana (+szczęście)'),('workshop','Warsztat (+produkcja)'),
            ('market','Rynek (+mały dochód)'),('farm','Farma (+produkcja)'),('sawmill','Tartak (+drewno)'),
            ('quarry','Kamieniołom (+kamień)'),('school','Szkoła (+badania)'),('hospital','Szpital (+szczęście)'),
        ]
        for b_key, label in building_infos:
            btn = ttk.Button(build_frame, text=f'{label}', command=lambda bk=b_key: self.build(bk))
            btn.grid(row=row, column=0, sticky='ew', pady=3)
            lbl = ttk.Label(build_frame, text=f'Ilość: 0', width=12)
            lbl.grid(row=row, column=1, sticky='w')
            self.build_buttons[b_key] = lbl
            row += 1
        ttk.Separator(build_frame).grid(row=row, column=0, columnspan=2, sticky='ew', pady=8); row += 1
        ttk.Button(build_frame, text='Sprzedaj zasoby (dynamiczne)', command=self.open_sell_dialog).grid(row=row, column=0, sticky='ew'); row += 1
        ttk.Button(build_frame, text='Kup zasoby (dynamiczne)', command=self.open_buy_dialog).grid(row=row, column=0, sticky='ew'); row += 1

        # akcje i prawa kolumna
        right_frame = ttk.LabelFrame(self, text='Działania', padding=8)
        right_frame.place(x=770, y=10, width=230, height=520)
        ttk.Button(right_frame, text='Zatrudnij menadżera', command=self.open_hire_manager).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Pobierz podatek', command=self.collect_taxes).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Zorganizuj festyn', command=self.festival).pack(fill='x', pady=4)
        ttk.Separator(right_frame).pack(fill='x', pady=6)
        ttk.Button(right_frame, text='Koniec dnia', command=self.end_day).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Toggle Auto-Dzień', command=self.toggle_auto_day).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Prestige (Reset)', command=self.perform_prestige).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Zapisz (slot1)', command=lambda: self.save_game(0)).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Wczytaj (slot1)', command=lambda: self.load_game(0)).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Nowa gra', command=self.new_game_prompt).pack(fill='x', pady=4)
        ttk.Separator(right_frame).pack(fill='x', pady=6)
        ttk.Button(right_frame, text='Ulepszenia', command=self.open_upgrades).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Questy', command=self.show_quests).pack(fill='x', pady=4)
        ttk.Button(right_frame, text='Osiągnięcia', command=self.show_achievements).pack(fill='x', pady=4)

        # log
        log_frame = ttk.LabelFrame(self, text='Log', padding=8)
        log_frame.place(x=10, y=280, width=320, height=270)
        self.log_text = tk.Text(log_frame, state='disabled', wrap='word')
        self.log_text.pack(expand=True, fill='both')

    # --- market dynamics ---
    def open_sell_dialog(self):
        win = tk.Toplevel(self); win.title('Sprzedaj zasoby')
        ttk.Label(win, text='Zasób:').grid(row=0, column=0)
        res_var = tk.StringVar(value='wood')
        ttk.Radiobutton(win, text='Drewno', variable=res_var, value='wood').grid(row=0, column=1)
        ttk.Radiobutton(win, text='Kamień', variable=res_var, value='stone').grid(row=0, column=2)
        ttk.Label(win, text='Ilość:').grid(row=1, column=0)
        qty_var = tk.IntVar(value=100)
        ttk.Entry(win, textvariable=qty_var).grid(row=1, column=1)
        price_lbl = ttk.Label(win, text='')
        price_lbl.grid(row=2, column=0, columnspan=3)
        def price_for(qty, res):
            base = MARKET_BASE[res]
            # duża sprzedaż obniża cenę (slippage)
            mult = max(0.5, 1 - min(qty / 50000.0, 0.5))
            return int(base * SELL_SPREAD * mult * qty)
        def update_price():
            r = res_var.get(); qty = max(0, qty_var.get()); price_lbl.config(text=f'Cena sprzedaży: {price_for(qty,r)}$')
        def do_sell():
            r = res_var.get(); qty = max(0, qty_var.get())
            if qty <= 0: return
            if r == 'wood' and qty > self.game.wood: messagebox.showinfo('Brak','Nie masz tyle drewna'); return
            if r == 'stone' and qty > self.game.stone: messagebox.showinfo('Brak','Nie masz tyle kamienia'); return
            price = price_for(qty, r)
            if r == 'wood': self.game.wood -= qty
            else: self.game.stone -= qty
            self.game.money += price
            self.log(f'Sprzedano {qty} {r} za {price}$')
            self.refresh_all(); win.destroy()
        ttk.Button(win, text='Aktualizuj', command=update_price).grid(row=3, column=0)
        ttk.Button(win, text='Sprzedaj', command=do_sell).grid(row=3, column=1)
        update_price()

    def open_buy_dialog(self):
        win = tk.Toplevel(self); win.title('Kup zasoby')
        ttk.Label(win, text='Zasób:').grid(row=0, column=0)
        res_var = tk.StringVar(value='wood')
        ttk.Radiobutton(win, text='Drewno', variable=res_var, value='wood').grid(row=0, column=1)
        ttk.Radiobutton(win, text='Kamień', variable=res_var, value='stone').grid(row=0, column=2)
        ttk.Label(win, text='Ilość:').grid(row=1, column=0)
        qty_var = tk.IntVar(value=100)
        ttk.Entry(win, textvariable=qty_var).grid(row=1, column=1)
        price_lbl = ttk.Label(win, text='')
        price_lbl.grid(row=2, column=0, columnspan=3)
        def price_for(qty, res):
            base = MARKET_BASE[res]
            mult = 1 + min(qty / 20000.0, 2.0)  # duży zakup windowe ceny
            return int(base * BUY_SPREAD * mult * qty)
        def update_price():
            r = res_var.get(); qty = max(0, qty_var.get()); price_lbl.config(text=f'Cena zakupu: {price_for(qty,r)}$')
        def do_buy():
            r = res_var.get(); qty = max(0, qty_var.get())
            if qty <= 0: return
            price = price_for(qty, r)
            if self.game.money < price: messagebox.showinfo('Brak','Nie masz wystarczająco pieniędzy'); return
            self.game.money -= price
            if r == 'wood': self.game.wood += qty
            else: self.game.stone += qty
            self.log(f'Kupiono {qty} {r} za {price}$')
            self.refresh_all(); win.destroy()
        ttk.Button(win, text='Aktualizuj', command=update_price).grid(row=3, column=0)
        ttk.Button(win, text='Kup', command=do_buy).grid(row=3, column=1)
        update_price()

    # --- budowanie ---
    def build(self, kind):
        base_costs = {
            'house': {'money':200,'wood':20,'stone':5}, 'pavilion':{'money':150,'wood':10},
            'workshop':{'money':300,'wood':30,'stone':10}, 'market':{'money':250,'wood':15,'stone':10},
            'farm':{'money':180,'wood':5}, 'sawmill':{'money':250}, 'quarry':{'money':250},
            'school':{'money':400,'wood':20}, 'hospital':{'money':600,'wood':30,'stone':20},
        }
        cost = base_costs.get(kind, {})
        # reduced build costs upgrade
        discount = 0.95 if self.game.upgrades.get('reduced_build_costs') else 1.0
        money_cost = int(cost.get('money',0) * discount)
        wood_cost = int(cost.get('wood',0) * discount)
        stone_cost = int(cost.get('stone',0) * discount)
        if self.game.money < money_cost or self.game.wood < wood_cost or self.game.stone < stone_cost:
            messagebox.showinfo('Brak zasobów','Nie masz wystarczająco zasobów.'); return
        self.game.money -= money_cost; self.game.wood -= wood_cost; self.game.stone -= stone_cost
        self.game.buildings[kind] = self.game.buildings.get(kind,0) + 1
        self.log(f'Wybudowano {kind}. Ilość: {self.game.buildings[kind]}')
        self.refresh_all()

    # --- managerowie ---
    def open_hire_manager(self):
        win = tk.Toplevel(self); win.title('Zatrudnij menadżera')
        ttk.Label(win, text='Wybierz menadżera (koszt zatrudnienia):').pack()
        managers = [
            ('Jacek (5% baza dochodów)',5,1000,'base_income'),
            ('Monika (10% baza dochodów)',10,2500,'base_income'),
            ('Joanna (redukcja kosztów budowy 5%)',3,1500,'reduce_costs'),
            ('Mariusz (15% produkcji budynków)',15,5000,'prod_boost'),
        ]
        sel = tk.IntVar(value=-1)
        for i,m in enumerate(managers): ttk.Radiobutton(win, text=f'{m[0]} - koszt {m[2]}$', variable=sel, value=i).pack(anchor='w')
        def hire():
            i = sel.get();
            if i<0: return
            name, bonus, cost, role = managers[i]
            if self.game.money < cost: messagebox.showinfo('Brak','Nie masz pieniędzy'); return
            self.game.money -= cost
            self.game.manager = name.split(' ')[0]; self.game.manager_bonus = bonus
            if role == 'reduce_costs': self.game.upgrades['reduced_build_costs'] = True; self.game.manager_bonus = 0
            if role == 'prod_boost': self.game.upgrades['manager_prod'] = True; self.game.manager_bonus = 0
            self.log(f'Zatrudniono {self.game.manager} (premia {bonus}%). Koszt: {cost}$')
            self.refresh_all(); win.destroy()
        ttk.Button(win, text='Zatrudnij', command=hire).pack(pady=6)

    # --- taxes / festyn ---
    def collect_taxes(self):
        tax = simpledialog.askinteger('Podatki','Ile pieniędzy pobrać?',parent=self,minvalue=0)
        if tax is None: return
        self.game.money += tax; lost = tax//5; self.game.happiness -= lost
        self.log(f'Pobrano {tax}$ podatków (-{lost} szczęścia)'); self.refresh_all()

    def festival(self):
        if self.game.money < 200: messagebox.showinfo('Brak','Nie masz pieniędzy'); return
        self.game.money -= 200; self.game.happiness += 20
        self.log('Zorganizowano festyn (-200$, +20 szczęścia)'); self.refresh_all()

    # --- end day / auto-day ---
    def end_day(self):
        produced, event_text = self.game.end_day()
        self.log(f'Koniec dnia. Produkcja: +{produced.get("money",0)}$, +{produced.get("wood",0)}w, +{produced.get("stone",0)}k. Wydarzenie: {event_text}')
        ok, msg = self.game.save(SAVE_SLOTS[0])
        if ok: self.log(msg)
        else: self.log('Błąd zapisu: '+msg)
        self.refresh_all()

    def toggle_auto_day(self):
        self.auto_day = not self.auto_day
        if self.auto_day: self.log('Auto-dzień WŁĄCZONY'); self.run_auto_day()
        else:
            self.log('Auto-dzień WYŁĄCZONY');
            if self.auto_after_id: self.after_cancel(self.auto_after_id); self.auto_after_id=None

    def run_auto_day(self):
        if not self.auto_day: return
        self.end_day(); self.auto_after_id = self.after(self.auto_interval, self.run_auto_day)

    # --- save/load ---
    def save_game(self, slot_idx=0):
        ok,msg = self.game.save(SAVE_SLOTS[slot_idx])
        if ok: self.log(msg); messagebox.showinfo('Zapis',msg)
        else: self.log('Błąd zapisu: '+msg); messagebox.showerror('Błąd zapisu',msg)

    def load_game(self, slot_idx=0):
        ok,msg = self.game.load(SAVE_SLOTS[slot_idx])
        if ok: self.log(msg); messagebox.showinfo('Wczytano',msg); self.refresh_all()
        else: self.log('Błąd wczytania: '+msg); messagebox.showerror('Błąd',msg)

    # --- upgrades (non-modal logging) ---
    def open_upgrades(self):
        win = tk.Toplevel(self); win.title('Ulepszenia'); win.geometry('360x220')
        ttk.Label(win, text=f'Punkty badań: {self.game.research_points}').pack(pady=6)
        def buy(name,cost,func):
            if self.game.research_points < cost: self.log('Brak punktów badań'); return
            self.game.research_points -= cost; func(); self.log(f'Kupiono ulepszenie: {name} (koszt {cost})'); self.refresh_all()
        def better_tools(): self.game.upgrades['better_tools']=True
        def market_reforms(): self.game.upgrades['market_reforms']=True
        def reduced_build_costs(): self.game.upgrades['reduced_build_costs']=True
        def manager_prod(): self.game.upgrades['manager_prod']=True
        ttk.Button(win, text='Better Tools (10 pkt)', command=lambda: buy('Better Tools',10,better_tools)).pack(fill='x',padx=12,pady=6)
        ttk.Button(win, text='Market Reforms (6 pkt)', command=lambda: buy('Market Reforms',6,market_reforms)).pack(fill='x',padx=12,pady=6)
        ttk.Button(win, text='Reduced Build Costs (8 pkt)', command=lambda: buy('Reduced Costs',8,reduced_build_costs)).pack(fill='x',padx=12,pady=6)
        ttk.Button(win, text='Manager Production (12 pkt)', command=lambda: buy('Manager Prod',12,manager_prod)).pack(fill='x',padx=12,pady=6)

    # --- quests / achievements ---
    def show_quests(self):
        win = tk.Toplevel(self); win.title('Questy'); win.geometry('420x260')
        for qid,q in self.game.quests.items():
            status = 'ZROBIONE' if q.get('done') else 'AKTYWNE'
            ttk.Label(win, text=f"{q['desc']} - {status}").pack(anchor='w', padx=8, pady=2)

    def show_achievements(self):
        ach = '\n'.join(sorted(list(self.game.achievements))) or 'Brak'
        messagebox.showinfo('Osiągnięcia', ach)

    # --- prestige UI ---
    def perform_prestige(self):
        if not self.game.can_prestige(): messagebox.showinfo('Prestige', 'Nie masz jeszcze wymagan, zebrać wiecej!'); return
        pts = self.game.prestige_value_if_reset()
        if not messagebox.askyesno('Prestige', f'Prestige da ci {pts} punktów. Potwierdzić reset?'):
            return
        ok, msg = self.game.do_prestige()
        if ok:
            messagebox.showinfo('Prestige', msg)
            self.log(msg)
            self.refresh_all()
        else:
            messagebox.showinfo('Prestige', msg)

    # --- utilities ---
    def log(self, text):
        self.log_text.config(state='normal')
        self.log_text.insert('end', f'[Dzień {self.game.day}] {text}\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def refresh_all(self):
        self.lbl_city.config(text=f'Miasto: {self.game.playername} (Prestige x{1 + self.game.prestige_points*0.02:.2f})')
        self.lbl_day.config(text=f'Dzień: {self.game.day}')
        self.lbl_money.config(text=f'Pieniądze: {self.game.money}')
        self.lbl_pop.config(text=f'Populacja: {self.game.population}')
        self.lbl_happy.config(text=f'Szczęście: {self.game.happiness}')
        self.lbl_wood.config(text=f'Drewno: {self.game.wood}')
        self.lbl_stone.config(text=f'Kamień: {self.game.stone}')
        self.lbl_manager.config(text=f'Menadżer: {self.game.manager} (+{self.game.manager_bonus}%)')
        self.lbl_research.config(text=f'Punkty badań: {self.game.research_points}')
        for k,lbl in self.build_buttons.items(): lbl.config(text=f'Ilość: {self.game.buildings.get(k,0)}')
        # prestige display
        self.lbl_prestige.config(text=f'Prestige: {self.game.prestige_points} pts')
        # progress to next prestige: based on money requirement (simple)
        cur = min(self.game.money, PRESTIGE_MONEY_REQ)
        self.prestige_bar['maximum'] = PRESTIGE_MONEY_REQ
        self.prestige_bar['value'] = cur

    def new_game_prompt(self):
        name = simpledialog.askstring('Nowa gra','Podaj nazwę miasta:',parent=self)
        if name: self.game = CityGame(); self.game.playername=name; self.log(f'Nowa gra: {name}'); self.refresh_all()

    def on_quit(self):
        if messagebox.askyesno('Wyjście','Zapisać do slot1 przed wyjściem?'):
            self.game.save(SAVE_SLOTS[0])
        self.destroy()


if __name__ == '__main__':
    game = CityGame()
    app = CityGUI(game); app.mainloop()
