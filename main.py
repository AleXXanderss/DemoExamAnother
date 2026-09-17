import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import psycopg

DB = 'postgresql://postgres:123@localhost:5432/demoekz'
PIC = Path(__file__).parent / 'pictures'
LOCKED = 'Вы заблокированы. Обратитесь к администратору'
WRONG = 'Вы ввели неверный логин или пароль.\nПожалуйста проверьте ещё раз введенные данные'


def db(query, values=(), read=False):
    with psycopg.connect(DB) as connection:
        result = connection.execute(query, values)
        return result.fetchall() if read else None


class UI:
    def __init__(self, root):
        self.root = root
        root.title('Авторизация'); root.geometry('500x600')
    def label(self, parent, text, **options):
        return ttk.Label(parent, text=text, **options)
    def button(self, parent, text, command, padx=3):
        x = ttk.Button(parent, text=text, command=command); x.pack(side='left', padx=padx); return x
    def fields(self, parent, definitions, grid=False):
        entries = []
        for row, (text, show) in enumerate(definitions):
            label = self.label(parent, text); entry = ttk.Entry(parent, show=show)
            label.grid(row=row, column=0) if grid else label.pack(anchor='w')
            (entry.grid(row=row, column=1, sticky='ew') if grid else entry.pack(fill='x'))
            entries.append(entry)
        return entries
    def buttons(self, parent, definitions, padx=3):
        [self.button(parent, text, command, padx) for text, command in definitions]

    def clear(self):
        [x.destroy() for x in self.root.winfo_children()]

class App(UI):
    def __init__(self, root):
        super().__init__(root)
        self.login_page()
    def login_page(self):
        self.clear()
        box = ttk.Frame(self.root, padding=20)
        box.pack(fill='both', expand=True)
        self.label(box, 'Авторизация', font=('Arial', 18, 'bold')).pack(pady=8)
        self.login_entry, self.password_entry = self.fields(box, [('Логин', ''), ('Пароль', '*')])
        self.label(box, 'Соберите картинку').pack(pady=(14, 3))
        self.info = self.label(box, 'Выберите фрагмент и нажмите его место')
        self.info.pack()
        self.make_captcha(box)
        buttons = ttk.Frame(box); buttons.pack(pady=14)
        self.buttons(buttons, [('Войти', self.login), ('Сбросить', self.reset)])
    def make_captcha(self, box):
        self.selected, self.placed = None, {}
        self.images = {i: tk.PhotoImage(file=PIC / f'{i}.png').subsample(8, 8) for i in range(1, 5)}
        source = ttk.Frame(box); source.pack(pady=6)
        self.parts = {}
        for column, part in enumerate((1, 3, 2, 4)):
            item = tk.Label(source, image=self.images[part], cursor='hand2'); item.grid(row=0, column=column, padx=3)
            item.bind('<Button-1>', lambda event, value=part: self.select(value))
            item.bind('<ButtonRelease-1>', self.drop)
            self.parts[part] = item
        board = ttk.Frame(box); board.pack()
        self.slots = {}
        for place in range(1, 5):
            slot = tk.Label(board, text=place, width=10, height=5, bg='#eeeeee', relief='ridge')
            slot.grid(row=(place-1)//2, column=(place-1)%2, padx=3, pady=3)
            slot.bind('<ButtonRelease-1>', lambda event, value=place: self.put(value))
            self.slots[place] = slot
    def select(self, part):
        self.selected = part

    def drop(self, event):
        if self.selected:
            target = self.root.winfo_containing(self.root.winfo_pointerx(), self.root.winfo_pointery())
            for place, slot in self.slots.items():
                if target is slot: self.put(place)

    def put(self, place):
        if self.selected is None:
            return
        if place in self.placed:
            self.info.config(text='Это место уже занято')
            return
        p=self.selected; self.slots[place].config(image=self.images[p],text='',width=88,height=88); self.parts[p].grid_remove(); self.placed[place]=p; self.selected=None
        self.info.config(text='Капча собрана' if len(self.placed) == 4 else f'Размещено: {len(self.placed)}/4')

    def reset(self):
        for item in self.parts.values(): item.grid()
        for place, slot in self.slots.items(): slot.config(image='',text=place,width=10,height=5)
        self.placed.clear(); self.selected=None
        self.info.config(text='Выберите фрагмент и нажмите его место')

    def login(self):
        username, password = self.login_entry.get().strip().lower(), self.password_entry.get()
        if not username or not password:
            messagebox.showwarning('Пустые поля', 'Введите логин и пароль')
            return
        try:
            rows = db('SELECT username,password_hash,is_admin,failed_attempts,is_locked FROM users WHERE username=%s',(username,),1)
        except psycopg.Error as error:
            messagebox.showerror('Ошибка базы данных', str(error))
            return
        if not rows:
            messagebox.showerror('Ошибка входа', WRONG)
            return
        username, saved, admin, attempts, locked = rows[0]
        if locked:
            messagebox.showwarning('Учетная запись заблокирована', LOCKED)
            return
        if len(self.placed) != 4 or not all(self.placed.get(i)==i for i in range(1,5)) or password != saved:
            attempts += 1; locked = attempts >= 3
            db('UPDATE users SET failed_attempts=%s,is_locked=%s WHERE username=%s',(attempts,locked,username))
            messagebox.showwarning('Ошибка входа', LOCKED if locked else f'Неверные данные. Попыток: {attempts}/3')
            self.reset()
            return
        db('UPDATE users SET failed_attempts=0 WHERE username=%s', (username,))
        self.admin_page() if admin else self.user_page()

    def user_page(self):
        self.clear()
        self.label(self.root, 'Вы успешно авторизовались', font=('Arial', 16, 'bold')).pack(pady=70)
        ttk.Button(self.root, text='Выйти', command=self.login_page).pack()

    def admin_page(self):
        self.clear()
        box = ttk.Frame(self.root, padding=12); box.pack(fill='both', expand=True)
        self.label(box, 'Пользователи', font=('Arial', 16, 'bold')).pack()
        form = ttk.Frame(box); form.pack(fill='x', pady=8)
        self.edit_login, self.edit_password = self.fields(form, [('Логин', ''), ('Пароль', '*')], grid=True)
        form.columnconfigure(1, weight=1)
        self.edit_id = None
        for column, (text, command) in enumerate((('Сохранить', self.save), ('Очистить', self.clear_form))):
            ttk.Button(form, text=text, command=command).grid(row=2, column=column, pady=5)
        self.tree = ttk.Treeview(box, columns=('login', 'role', 'state'), show='headings', height=12)
        for column, title in zip(('login', 'role', 'state'), ('Логин', 'Роль', 'Статус')):
            self.tree.heading(column, text=title)
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', self.edit)
        buttons = ttk.Frame(box); buttons.pack(pady=7)
        self.buttons(buttons, [('Изменить', self.edit), ('Разблокировать', self.unlock), ('Удалить', self.delete), ('Выйти', self.login_page)], padx=2)
        self.load()

    def load(self):
        self.tree.delete(*self.tree.get_children())
        for user_id, username, admin, locked in db('SELECT id_user,username,is_admin,is_locked FROM users ORDER BY username',read=1):
            self.tree.insert('', 'end', iid=user_id, values=(username,
                'Администратор' if admin else 'Пользователь', 'Заблокирован' if locked else 'Активен'))

    def selected_id(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning('Нет выбора', 'Выберите пользователя')
            return None
        return int(selected[0])

    def edit(self, event=None):
        user_id = self.selected_id()
        if user_id is None:
            return
        username = db('SELECT username FROM users WHERE id_user=%s', (user_id,), True)[0][0]
        self.edit_id = user_id
        self.edit_login.delete(0, 'end')
        self.edit_login.insert(0, username)
        self.edit_password.delete(0, 'end')

    def clear_form(self):
        self.edit_id=None; self.edit_login.delete(0,'end'); self.edit_password.delete(0,'end')

    def save(self):
        username, password = self.edit_login.get().strip().lower(), self.edit_password.get()
        if not username or self.edit_id is None and not password:
            messagebox.showwarning('Пустые поля', 'Введите логин и пароль')
            return
        try:
            if self.edit_id is None:
                db('INSERT INTO users(username,password_hash) VALUES(%s,%s)', (username, password))
            elif password:
                db('UPDATE users SET username=%s,password_hash=%s WHERE id_user=%s',(username,password,self.edit_id))
            else:
                db('UPDATE users SET username=%s WHERE id_user=%s', (username, self.edit_id))
            self.clear_form(); self.load()
        except psycopg.errors.UniqueViolation:
            messagebox.showerror('Ошибка', 'Пользователь с таким логином уже существует')

    def unlock(self):
        user_id = self.selected_id()
        if user_id:
            db('UPDATE users SET failed_attempts=0,is_locked=FALSE WHERE id_user=%s', (user_id,))
            self.load()

    def delete(self):
        user_id = self.selected_id()
        if user_id:
            db('DELETE FROM users WHERE id_user=%s AND is_admin=FALSE', (user_id,))
            self.load()


root = tk.Tk()
App(root)
root.mainloop()
