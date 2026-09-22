import html
import os
import re
import struct
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import xml.etree.ElementTree as ET
import zipfile
import google.generativeai as genai
import pypdf

# SEM VLOŽ SVOJ KĽÚČ
API_KLUC = "YOUR_GEMINI_API_KEY_HERE"
genai.configure(api_key=API_KLUC)

# Aktuálny odporúčaný model s vysokým limitom
model = genai.GenerativeModel("gemini-3.5-flash-lite")

# Tmavé farby
FARBA_POZADIA = "#1e1e1e"
FARBA_PANELOV = "#252526"
FARBA_TEXTU = "#e0e0e0"
FARBA_VSTUPU = "#181818"


class PrekladacApp:

  def __init__(self, root):
    self.root = root
    self.root.title("Prekladač kníh (CZ/EN -> SK/CZ)")
    self.root.configure(bg=FARBA_POZADIA)

    sirka = int(self.root.winfo_screenwidth() * 0.9)
    vyska = int(self.root.winfo_screenheight() * 0.85)
    self.root.geometry(f"{sirka}x{vyska}+50+30")

    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TFrame", background=FARBA_POZADIA)
    style.configure("Panel.TFrame", background=FARBA_PANELOV)
    style.configure(
        "Dark.TLabel",
        background=FARBA_PANELOV,
        foreground=FARBA_TEXTU,
        font=("Helvetica", 12),
    )
    style.configure(
        "Status.TLabel",
        background=FARBA_PANELOV,
        foreground="#4ec9b0",
        font=("Helvetica", 13, "bold"),
    )
    style.configure(
        "Dark.TButton",
        background="#3c3c3c",
        foreground=FARBA_TEXTU,
        font=("Helvetica", 12, "bold"),
        padding=8,
        borderwidth=1,
    )
    style.map(
        "Dark.TButton",
        background=[("active", "#505050"), ("disabled", "#2a2a2a")],
    )

    style.configure(
        "Dark.TRadiobutton",
        background=FARBA_PANELOV,
        foreground=FARBA_TEXTU,
        font=("Helvetica", 11, "bold"),
    )

    frame_top = ttk.Frame(root, style="Panel.TFrame", padding=15)
    frame_top.pack(fill="x", padx=10, pady=(10, 5))

    self.btn_subor = ttk.Button(
        frame_top,
        text="Vybrať knihu (.epub / .docx / .rtf / .txt / .pdf / .pdb)",
        style="Dark.TButton",
        command=self.nacitat_subor,
    )
    self.btn_subor.pack(side="left", padx=5)

    self.lbl_subor = ttk.Label(
        frame_top,
        text="Žiadny súbor nevybraný",
        style="Dark.TLabel",
        foreground="#888888",
    )
    self.lbl_subor.pack(side="left", padx=15)

    frame_text = tk.Frame(root, bg=FARBA_POZADIA, padx=10, pady=5)
    frame_text.pack(fill="both", expand=True)

    scrollbar = tk.Scrollbar(frame_text, bg=FARBA_PANELOV)
    scrollbar.pack(side="right", fill="y")

    self.txt_vstup = tk.Text(
        frame_text,
        wrap="word",
        font=("Helvetica", 14),
        bg=FARBA_VSTUPU,
        fg=FARBA_TEXTU,
        insertbackground="white",
        selectbackground="#264f78",
        relief="flat",
        padx=15,
        pady=15,
        yscrollcommand=scrollbar.set,
    )
    self.txt_vstup.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=self.txt_vstup.yview)

    frame_bottom = ttk.Frame(root, style="Panel.TFrame", padding=15)
    frame_bottom.pack(fill="x", padx=10, pady=(5, 10))

    self.btn_start = ttk.Button(
        frame_bottom,
        text="Spustiť preklad",
        style="Dark.TButton",
        command=self.start_prekladu,
    )
    self.btn_start.pack(side="left", padx=5)

    self.smer_var = tk.StringVar(value="cz_sk")

    self.rb1 = ttk.Radiobutton(
        frame_bottom,
        text="CZ → SK",
        variable=self.smer_var,
        value="cz_sk",
        style="Dark.TRadiobutton",
    )
    self.rb1.pack(side="left", padx=10)

    self.rb2 = ttk.Radiobutton(
        frame_bottom,
        text="EN → SK",
        variable=self.smer_var,
        value="en_sk",
        style="Dark.TRadiobutton",
    )
    self.rb2.pack(side="left", padx=5)

    self.rb3 = ttk.Radiobutton(
        frame_bottom,
        text="EN → CZ",
        variable=self.smer_var,
        value="en_cz",
        style="Dark.TRadiobutton",
    )
    self.rb3.pack(side="left", padx=5)

    self.lbl_status = ttk.Label(
        frame_bottom, text="Pripravený", style="Status.TLabel"
    )
    self.lbl_status.pack(side="left", padx=20)

  def nacitat_docx(self, cesta):
    odstavce = []
    with zipfile.ZipFile(cesta, "r") as z:
      xml_obsah = z.read("word/document.xml")
      koren = ET.fromstring(xml_obsah)
      ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
      for p in koren.iter(f"{{{ns}}}p"):
        kusky = [
            t.text
            for t in p.iter(f"{{{ns}}}t")
            if t.text is not None and t.text != ""
        ]
        if kusky:
          odstavce.append("".join(kusky))
    return "\n\n".join(odstavce)

  def nacitat_epub_jednoduse(self, cesta):
    text_celkovy = []
    with zipfile.ZipFile(cesta, "r") as z:
      subory = [
          f
          for f in z.namelist()
          if f.endswith(".xhtml") or f.endswith(".html") or f.endswith(".htm")
      ]
      subory.sort()
      for f in subory:
        surovy_html = z.read(f).decode("utf-8", errors="ignore")
        cisty_text = re.sub(r"<[^>]+>", " ", surovy_html)
        cisty_text = html.unescape(cisty_text)
        riadky = [r.strip() for r in cisty_text.splitlines() if r.strip()]
        if riadky:
          text_celkovy.append("\n".join(riadky))
    return "\n\n".join(text_celkovy)

  def nacitat_rtf(self, cesta):
    with open(cesta, "r", encoding="utf-8", errors="ignore") as f:
      obsah = f.read()
    text = re.sub(r"\\([a-z]{1,32})(-?\d+)? ?|\\\'[0-9a-fA-F]{2}", " ", obsah)
    text = re.sub(r"[{}\\]", "", text)
    riadky = [r.strip() for r in text.splitlines() if r.strip()]
    return "\n\n".join(riadky)

  def nacitat_pdf(self, cesta):
    text_celkovy = []
    with open(cesta, "rb") as f:
      citatel = pypdf.PdfReader(f)
      for strana in citatel.pages:
        text_strany = strana.extract_text()
        if text_strany:
          text_celkovy.append(text_strany.strip())
    return "\n\n".join(text_celkovy)

  def dekomprimuj_palmdoc(self, data):
    i = 0
    dlzka = len(data)
    vystup = bytearray()
    while i < dlzka:
      b = data[i]
      i += 1
      if 1 <= b <= 8:
        vystup.extend(data[i : i + b])
        i += b
      elif b <= 0x7F:
        vystup.append(b)
      elif b >= 0xC0:
        vystup.append(0x20)  # medzera
        vystup.append(b ^ 0x80)
      else:  # 0x80 az 0xBF (LZ77 par: posun a dlzka)
        if i >= dlzka:
          break
        b2 = data[i]
        i += 1
        posun = ((b & 0x3F) << 3) | (b2 >> 5)
        pocet = (b2 & 0x07) + 3
        start = len(vystup) - posun
        for _ in range(pocet):
          if start >= 0 and start < len(vystup):
            vystup.append(vystup[start])
            start += 1
    return bytes(vystup)

  def nacitat_pdb(self, cesta):
    with open(cesta, "rb") as f:
      raw = f.read()

    if len(raw) < 78:
      raise ValueError("Súbor PDB je poškodený alebo príliš malý.")

    pocet_zaznamov = struct.unpack(">H", raw[76:78])[0]
    offsets = []
    for i in range(pocet_zaznamov):
      offset = struct.unpack(">I", raw[78 + i * 8 : 82 + i * 8])[0]
      offsets.append(offset)
    offsets.append(len(raw))

    # Záznam 0 obsahuje hlavičku PalmDOC
    rekord0 = raw[offsets[0] : offsets[1]]
    kompresia = 1
    pocet_textovych = pocet_zaznamov - 1
    if len(rekord0) >= 16:
      kompresia = struct.unpack(">H", rekord0[0:2])[0]
      pocet_textovych = struct.unpack(">H", rekord0[8:10])[0]

    pocet_na_spracovanie = min(pocet_textovych, pocet_zaznamov - 1)
    dekomprimovane_bajty = bytearray()

    for idx in range(1, pocet_na_spracovanie + 1):
      blok = raw[offsets[idx] : offsets[idx + 1]]
      if kompresia == 2:
        dekomprimovane_bajty.extend(self.dekomprimuj_palmdoc(blok))
      else:
        dekomprimovane_bajty.extend(blok)

    # Detekcia kódovania textu (staré české/slovenské PDB knihy bývajú v cp1250)
    for kodovanie in ("cp1250", "utf-8", "iso-8859-2", "latin1"):
      try:
        return dekomprimovane_bajty.decode(kodovanie)
      except UnicodeDecodeError:
        continue

    return dekomprimovane_bajty.decode("latin1", errors="ignore")

  def nacitat_subor(self):
    cesta = filedialog.askopenfilename(
        filetypes=[
            (
                "Podporované dokumenty",
                "*.epub *.docx *.rtf *.txt *.pdf *.pdb",
            ),
            ("PDB knihy", "*.pdb"),
            ("PDF dokumenty", "*.pdf"),
            ("EPUB knihy", "*.epub"),
            ("Word dokumenty", "*.docx"),
            ("RTF dokumenty", "*.rtf"),
            ("Textové súbory", "*.txt"),
            ("Všetky súbory", "*.*"),
        ]
    )
    if not cesta:
      return

    self.lbl_subor.config(text=os.path.basename(cesta), foreground=FARBA_TEXTU)
    self.lbl_status.config(text="Načítavam...", foreground="#dcdcaa")
    self.root.update()

    try:
      pripona = cesta.lower()
      if pripona.endswith(".docx"):
        obsah = self.nacitat_docx(cesta)
      elif pripona.endswith(".epub"):
        obsah = self.nacitat_epub_jednoduse(cesta)
      elif pripona.endswith(".rtf"):
        obsah = self.nacitat_rtf(cesta)
      elif pripona.endswith(".pdf"):
        obsah = self.nacitat_pdf(cesta)
      elif pripona.endswith(".pdb"):
        obsah = self.nacitat_pdb(cesta)
      else:
        with open(cesta, "r", encoding="utf-8", errors="ignore") as f:
          obsah = f.read()

      self.txt_vstup.delete("1.0", tk.END)
      self.txt_vstup.insert("1.0", obsah)
      self.lbl_status.config(
          text="Dokument načítaný. Pripravený na preklad.",
          foreground="#4ec9b0",
      )
    except Exception as e:
      messagebox.showerror("Chyba", f"Nepodarilo sa načítať súbor:\n{e}")
      self.lbl_status.config(text="Chyba pri načítaní.", foreground="#f44747")

  def start_prekladu(self):
    text = self.txt_vstup.get("1.0", tk.END).strip()
    if not text:
      messagebox.showwarning("Upozornenie", "Najprv načítaj dokument.")
      return

    self.btn_start.config(state="disabled")
    self.btn_subor.config(state="disabled")
    self.rb1.config(state="disabled")
    self.rb2.config(state="disabled")
    self.rb3.config(state="disabled")

    vlakno = threading.Thread(
        target=self.vykonaj_preklad, args=(text,), daemon=True
    )
    vlakno.start()

  def rozdel_kapitoly(self, text):
    bloky = re.split(
        r"(?i)(?=(?:kapitola\s+\d+|hlava\s+\d+|chapter\s+\d+))", text
    )
    kapitoly = [k.strip() for k in bloky if k.strip()]
    vysledok = []
    limit = 3500
    for k in kapitoly:
      if len(k) > limit:
        for i in range(0, len(k), limit):
          vysledok.append(k[i : i + limit])
      else:
        vysledok.append(k)
    return vysledok

  def vykonaj_preklad(self, text):
    kapitoly = self.rozdel_kapitoly(text)
    pocet = len(kapitoly)

    smer = self.smer_var.get()
    if smer == "cz_sk":
      vystupny_nazov = "prelozena_kniha_sk.txt"
      instrukcia = (
          "Prelož nasledujúci český text do kultivovanej, prirodzenej a"
          " spisovnej slovenčiny. Dôsledne sa vyhni bohemizmom, dodržuj"
          " slovenskú vetnú skladbu a zachovaj literárny štýl románu. Vráť"
          " výhradne samotný slovenský preklad bez komentárov:\n\n"
      )
    elif smer == "en_sk":
      vystupny_nazov = "prelozena_kniha_sk.txt"
      instrukcia = (
          "Prelož nasledujúci anglický text do kultivovanej, prirodzenej a"
          " spisovnej slovenčiny. Vyhni sa doslovnému prekladu a anglicizmom,"
          " dodržuj slovenskú vetnú skladbu a zachovaj literárny štýl románu."
          " Vráť výhradne samotný slovenský preklad bez komentárov:\n\n"
      )
    else:  # en_cz
      vystupny_nazov = "prelozena_kniha_cz.txt"
      instrukcia = (
          "Přelož následující anglický text do kultivované, přirozené a"
          " spisovné češtiny. Vyhni se doslovnému překladu a anglicismům,"
          " dodržuj český literární styl románu a českoslovosled. Vrať"
          " výhradně samotný český překlad bez komentářů:\n\n"
      )

    vystup = os.path.expanduser(f"~/Desktop/{vystupny_nazov}")

    with open(vystup, "w", encoding="utf-8") as f:
      f.write("")

    posledna_chyba = ""
    uspesne_zapisane = 0

    for i, kap in enumerate(kapitoly, start=1):
      self.lbl_status.config(
          text=f"Prekladám časť {i} z {pocet}...", foreground="#dcdcaa"
      )

      prompt = f"{instrukcia}{kap}"

      uspech = False
      pokusy = 0
      while not uspech and pokusy < 3:
        try:
          odpoved = model.generate_content(prompt)
          preklad = odpoved.text
          if preklad:
            with open(vystup, "a", encoding="utf-8") as f:
              cisty_blok = "\n".join(
                  [r.strip() for r in preklad.splitlines() if r.strip()]
              )
              f.write(cisty_blok + "\n")
            uspech = True
            uspesne_zapisane += 1
            print(f"[OK] Časť {i}/{pocet} zapísaná.")
        except Exception as e:
          pokusy += 1
          posledna_chyba = str(e)
          print(f"[CHYBA] Časť {i}, pokus {pokusy}: {e}")
          time.sleep(5)

      if not uspech:
        break

      time.sleep(10)

    self.btn_start.config(state="normal")
    self.btn_subor.config(state="normal")
    self.rb1.config(state="normal")
    self.rb2.config(state="normal")
    self.rb3.config(state="normal")

    if uspesne_zapisane == pocet:
      self.lbl_status.config(text="Preklad dokončený!", foreground="#4ec9b0")
      messagebox.showinfo(
          "Hotovo",
          f"Kniha bola úspešne preložená ({uspesne_zapisane} častí).\n\nSúbor"
          " nájdeš na Ploche:\n{vystupny_nazov}",
      )
    else:
      self.lbl_status.config(text="Preklad prerušený!", foreground="#f44747")
      messagebox.showerror(
          "Chyba prekladu",
          f"Preklad sa zastavil na časti {uspesne_zapisane + 1}.\n\nDôvod"
          f" chyby:\n{posledna_chyba}",
      )


if __name__ == "__main__":
  root = tk.Tk()
  app = PrekladacApp(root)
  root.mainloop()   