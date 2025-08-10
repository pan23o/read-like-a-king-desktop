import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import sqlite3
import os
import zipfile
import io
try:
    import fitz  # PyMuPDF for PDF
except Exception:
    fitz = None
from PIL import Image, ImageTk
import tempfile
import rarfile

DB = 'comics.db'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Read Like A King - Desktop (Prototipo)')
        self.geometry('800x600')
        self.conn = sqlite3.connect(DB)
        self.create_tables()
        self.create_ui()
        self.refresh_list()

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS comics (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            display_name TEXT,
            rating INTEGER DEFAULT 0,
            last_page INTEGER DEFAULT 0,
            total_pages INTEGER DEFAULT 0
        )''')
        self.conn.commit()

    def create_ui(self):
        frm = ttk.Frame(self)
        frm.pack(fill='both', expand=True)
        top = ttk.Frame(frm)
        top.pack(fill='x')
        ttk.Button(top, text='Añadir cómic/libro', command=self.add_files).pack(side='left', padx=5, pady=5)
        ttk.Button(top, text='Renombrar seleccionado', command=self.rename_selected).pack(side='left', padx=5)
        ttk.Button(top, text='Abrir carpeta de datos', command=self.open_data_folder).pack(side='left', padx=5)

        self.tree = ttk.Treeview(frm, columns=('name','rating','pages'), show='headings')
        self.tree.heading('name', text='Nombre')
        self.tree.heading('rating', text='Rating')
        self.tree.heading('pages', text='Páginas')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<Double-1>', self.on_open)

    def open_data_folder(self):
        import webbrowser
        webbrowser.open(os.path.abspath('.'))

    def add_files(self):
        paths = filedialog.askopenfilenames(title='Selecciona PDF/CBZ/CBR', filetypes=[('Archivos','*.pdf *.cbz *.cbr'),('Todos','*.*')])
        for p in paths:
            self.add_comic(p)
        self.refresh_list()

    def add_comic(self, path):
        name = os.path.basename(path)
        total = self.detect_total_pages(path)
        c = self.conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO comics(path, display_name, total_pages) VALUES (?,?,?)', (path, name, total))
            self.conn.commit()
        except Exception as e:
            print('DB error', e)

    def detect_total_pages(self, path):
        ext = path.lower().split('.')[-1]
        if ext == 'pdf' and fitz:
            try:
                doc = fitz.open(path)
                n = doc.page_count
                doc.close()
                return n
            except Exception:
                return 0
        if ext == 'cbz':
            try:
                with zipfile.ZipFile(path, 'r') as z:
                    imgs = [n for n in z.namelist() if n.lower().endswith(('.png','.jpg','.jpeg','.webp'))]
                    return len(imgs)
            except Exception:
                return 0
        if ext == 'cbr':
            try:
                rf = rarfile.RarFile(path)
                imgs = [n for n in rf.namelist() if n.lower().endswith(('.png','.jpg','.jpeg','.webp'))]
                return len(imgs)
            except Exception:
                return 0
        return 0

    def refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        c = self.conn.cursor()
        for row in c.execute('SELECT id, display_name, rating, total_pages FROM comics ORDER BY display_name'):
            self.tree.insert('', 'end', iid=row[0], values=(row[1], row[2], row[3]))

    def rename_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Info','Selecciona un cómic primero')
            return
        iid = sel[0]
        c = self.conn.cursor()
        row = c.execute('SELECT display_name FROM comics WHERE id=?',(iid,)).fetchone()
        if not row: return
        new = simpledialog.askstring('Renombrar','Nuevo nombre', initialvalue=row[0])
        if new:
            c.execute('UPDATE comics SET display_name=? WHERE id=?', (new, iid))
            self.conn.commit()
            self.refresh_list()

    def on_open(self, event):
        sel = self.tree.selection()
        if not sel: return
        iid = sel[0]
        c = self.conn.cursor()
        row = c.execute('SELECT path, display_name, rating, last_page, total_pages FROM comics WHERE id=?',(iid,)).fetchone()
        if not row: return
        path = row[0]
        DetailsWindow(self, path, iid)

class DetailsWindow(tk.Toplevel):
    def __init__(self, master, path, comic_id):
        super().__init__(master)
        self.path = path
        self.comic_id = comic_id
        self.title('Detalles - ' + os.path.basename(path))
        self.geometry('400x300')
        c = master.conn.cursor()
        row = c.execute('SELECT display_name, rating, last_page, total_pages FROM comics WHERE id=?',(comic_id,)).fetchone()
        name, rating, last_page, total_pages = row
        ttk.Label(self, text=name, font=('Arial',14)).pack(pady=5)
        ttk.Label(self, text=f'Páginas: {total_pages}').pack()
        frame = ttk.Frame(self)
        frame.pack(pady=10)
        self.stars = []
        for i in range(5):
            b = ttk.Button(frame, text='☆', command=lambda i=i: self.rate(i+1))
            b.grid(row=0, column=i, padx=2)
            self.stars.append(b)
        self.update_stars(rating)
        ttk.Button(self, text='Leer', command=self.open_reader).pack(side='left', padx=10, pady=10)
        ttk.Button(self, text='Cerrar', command=self.destroy).pack(side='right', padx=10, pady=10)

    def update_stars(self, rating):
        for i,b in enumerate(self.stars):
            b.config(text='★' if i < rating else '☆')

    def rate(self, value):
        c = self.master.conn.cursor()
        c.execute('UPDATE comics SET rating=? WHERE id=?',(value, self.comic_id))
        self.master.conn.commit()
        self.update_stars(value)

    def open_reader(self):
        ReaderWindow(self.master, self.path, self.comic_id)

class ReaderWindow(tk.Toplevel):
    def __init__(self, master, path, comic_id):
        super().__init__(master)
        self.path = path
        self.comic_id = comic_id
        self.title('Lector - ' + os.path.basename(path))
        self.geometry('900x700')
        self.canvas = tk.Canvas(self, bg='black')
        self.canvas.pack(fill='both', expand=True)
        self.btn_next = tk.Button(self, text='>', command=self.next_page)
        self.btn_prev = tk.Button(self, text='<', command=self.prev_page)
        self.btn_next.place_forget()
        self.btn_prev.place_forget()
        self.bind('<Motion>', self.on_motion)
        self.bind('<Key>', self.on_key)
        self.focus_set()
        self.tmpdir = tempfile.mkdtemp(prefix='rlak_')
        self.pages = []
        self.index = 0
        self.load_pages()
        self.show_page()

    def on_motion(self, event):
        # show buttons for 2 seconds
        w = self.winfo_width(); h = self.winfo_height()
        self.btn_next.place(x=w-60, y=h-60, width=50, height=50)
        self.btn_prev.place(x=10, y=h-60, width=50, height=50)
        if hasattr(self, 'hide_after'):
            self.after_cancel(self.hide_after)
        self.hide_after = self.after(2000, self.hide_buttons)

    def hide_buttons(self):
        self.btn_next.place_forget()
        self.btn_prev.place_forget()

    def on_key(self, event):
        if event.keysym in ('Right','space'):
            self.next_page()
        elif event.keysym=='Left':
            self.prev_page()

    def load_pages(self):
        ext = self.path.lower().split('.')[-1]
        if ext == 'pdf' and fitz:
            try:
                doc = fitz.open(self.path)
                for i in range(doc.page_count):
                    pix = doc.load_page(i).get_pixmap(dpi=150)
                    img_bytes = pix.tobytes('png')
                    self.pages.append(img_bytes)
                doc.close()
            except Exception as e:
                print('PDF error', e)
        elif ext == 'cbz':
            try:
                with zipfile.ZipFile(self.path, 'r') as z:
                    imgs = sorted([n for n in z.namelist() if n.lower().endswith(('.png','.jpg','.jpeg','.webp'))])
                    for name in imgs:
                        self.pages.append(z.read(name))
            except Exception as e:
                print('CBZ error', e)
        elif ext == 'cbr':
            try:
                rf = rarfile.RarFile(self.path)
                imgs = sorted([n for n in rf.namelist() if n.lower().endswith(('.png','.jpg','.jpeg','.webp'))])
                for name in imgs:
                    self.pages.append(rf.read(name))
            except Exception as e:
                print('CBR error', e)
        else:
            # fallback: single image
            try:
                with open(self.path, 'rb') as f:
                    self.pages.append(f.read())
            except Exception as e:
                print('file error', e)
        # update total_pages in DB
        c = self.master.conn.cursor()
        c.execute('UPDATE comics SET total_pages=? WHERE id=?', (len(self.pages), self.comic_id))
        self.master.conn.commit()

    def show_page(self):
        if not self.pages:
            self.canvas.delete('all')
            self.canvas.create_text(450,350, text='No hay páginas', fill='white')
            return
        data = self.pages[self.index]
        image = Image.open(io.BytesIO(data))
        # fit to canvas
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        iw, ih = image.size
        ratio = min(cw/iw, ch/ih)
        new_size = (int(iw*ratio), int(ih*ratio))
        image = image.resize(new_size, Image.ANTIALIAS)
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.delete('all')
        self.canvas.create_image(cw//2, ch//2, image=self.photo, anchor='center')
        # save progress
        c = self.master.conn.cursor()
        c.execute('UPDATE comics SET last_page=? WHERE id=?', (self.index, self.comic_id))
        self.master.conn.commit()

    def next_page(self):
        if self.index < len(self.pages)-1:
            self.index += 1
            self.show_page()

    def prev_page(self):
        if self.index > 0:
            self.index -= 1
            self.show_page()

if __name__ == '__main__':
    app = App()
    app.mainloop()
