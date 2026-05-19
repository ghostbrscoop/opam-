import os
import json
import winreg
import time
import ctypes
import pythoncom
from pathlib import Path

# Watchdog
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

import pystray
from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────
CONFIG_DIR  = Path(os.environ["APPDATA"]) / "GameToggle"
CONFIG_FILE = CONFIG_DIR / "config.json"
HIDDEN_DIR  = CONFIG_DIR / "hidden_shortcuts"
DESKTOP     = Path(os.environ["USERPROFILE"]) / "Desktop"
DESKTOP_PUB = Path("C:/Users/Public/Desktop")
LIST_FILE   = DESKTOP / "lista_jogos.txt"

LNK_KEYWORDS = [
    "riotclientservices.exe",
    "osulazer",
    "osu!.exe",
    "curseforge",
    "modrinth",
]

# ─────────────────────────────────────────
def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HIDDEN_DIR.mkdir(parents=True, exist_ok=True)

def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except:
        return {"hidden": False}

def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

# ─────────────────────────────────────────
def get_steam_apps_paths():
    paths = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        path, _ = winreg.QueryValueEx(key, "SteamPath")
        steamapps = Path(path.replace("/", "\\")) / "steamapps"
        if steamapps.exists():
            paths.append(steamapps)

        library_file = steamapps / "libraryfolders.vdf"
        if library_file.exists():
            content = library_file.read_text(encoding="utf-8", errors="ignore")
            import re
            for m in re.finditer(r'"path"\s+"([^"]+)"', content):
                lib_path = Path(m.group(1).replace("\\\\", "\\")) / "steamapps"
                if lib_path.exists():
                    paths.append(lib_path)
    except Exception as e:
        print(f"[DEBUG] Erro lendo SteamPath: {e}")
    return paths

def get_steam_game_ids():
    ids = set()
    for steam in get_steam_apps_paths():
        for f in steam.glob("appmanifest_*.acf"):
            m = f.stem.replace("appmanifest_", "")
            if m.isdigit():
                ids.add(m)
    print(f"[DEBUG] IDs de jogos detectados: {ids}")
    return ids

# ─────────────────────────────────────────
def is_steam_url(path: Path, steam_ids) -> bool:
    try:
        content = path.read_text(encoding="latin-1", errors="ignore")
        import re
        m = re.search(r"steam://rungameid/(\d+)", content)
        if m:
            gid = m.group(1)
            print(f"[DEBUG] .url encontrado: {path.name} → ID {gid}")
            return True  # aceita qualquer ID
    except Exception as e:
        print(f"[DEBUG] Erro lendo .url {path}: {e}")
    return False

def is_steam_lnk(path: Path, steam_ids) -> bool:
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        lnk   = shell.CreateShortcut(str(path))
        args  = (lnk.TargetPath + " " + lnk.Arguments).lower()
        import re
        m = re.search(r"(steam://rungameid/|applaunch\s)(\d+)", args)
        if m:
            gid = m.group(2)
            print(f"[DEBUG] .lnk Steam encontrado: {path.name} → ID {gid}")
            return True  # aceita qualquer ID
    except Exception as e:
        print(f"[DEBUG] Erro lendo .lnk {path}: {e}")
    return False

def is_game_lnk(path: Path) -> bool:
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        lnk   = shell.CreateShortcut(str(path))
        text  = (lnk.TargetPath + " " + lnk.Arguments).lower()
        if any(kw in text for kw in LNK_KEYWORDS):
            print(f"[DEBUG] .lnk não-Steam detectado: {path.name}")
            return True
    except Exception as e:
        print(f"[DEBUG] Erro lendo .lnk {path}: {e}")
    return False

# ─────────────────────────────────────────
def get_game_shortcuts():
    steam_ids = get_steam_game_ids()
    shortcuts = []

    for desktop in [DESKTOP, DESKTOP_PUB]:
        if not desktop.exists():
            continue

        for f in desktop.glob("*.url"):
            if is_steam_url(f, steam_ids):
                shortcuts.append(f)

        for f in desktop.glob("*.lnk"):
            if is_steam_lnk(f, steam_ids) or is_game_lnk(f):
                shortcuts.append(f)

    print(f"[DEBUG] Atalhos detectados: {[s.name for s in shortcuts]}")
    return shortcuts

def save_shortcut_list(shortcuts):
    try:
        with open(LIST_FILE, "w", encoding="utf-8") as f:
            for s in shortcuts:
                f.write(str(s) + "\n")
    except Exception as e:
        print("Erro ao salvar lista:", e)

def hide_games():
    shortcuts = get_game_shortcuts()
    save_shortcut_list(shortcuts)
    count = 0
    for src in shortcuts:
        dst = HIDDEN_DIR / src.name
        try:
            src.rename(dst)
            print(f"[DEBUG] Ocultando {src.name}")
            count += 1
        except Exception as e:
            print(f"[DEBUG] Falha ao ocultar {src.name}: {e}")
    return count

def show_games():
    count = 0
    for f in HIDDEN_DIR.iterdir():
        dst = DESKTOP / f.name
        try:
            f.rename(dst)
            count += 1
        except:
            pass
    return count

# ─────────────────────────────────────────
class DesktopHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        cfg = load_config()
        if not cfg.get("hidden"):
            return
        time.sleep(0.8)
        path = Path(event.src_path)
        ext  = path.suffix.lower()
        try:
            steam_ids = get_steam_game_ids()
            is_game = False
            if ext == ".url":
                is_game = is_steam_url(path, steam_ids)
            elif ext == ".lnk":
                is_game = is_steam_lnk(path, steam_ids) or is_game_lnk(path)
            if is_game:
                dst = HIDDEN_DIR / path.name
                path.rename(dst)
        except:
            pass

def start_watcher():
    if not HAS_WATCHDOG:
        return
    observer = Observer()
    observer.schedule(DesktopHandler(), str(DESKTOP), recursive=False)
    observer.daemon = True
    observer.start()

# ─────────────────────────────────────────
def make_icon(letter, bg, fg):
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=bg)
    try:
        font = ImageFont.truetype("segoeui.ttf", 32)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), letter, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((64 - w) / 2 - bbox[0], (64 - h) / 2 - bbox[1]), letter, font=font, fill=fg)
    return img

ICON_VISIBLE = make_icon("G", (20, 20, 20), (0, 200, 100))
ICON_HIDDEN  = make_icon("G", (200, 40, 40), (255, 255, 255))

tray_icon = None

def do_toggle(icon, item=None):
    cfg = load_config()
    if cfg["hidden"]:
        count = show_games()
        cfg["hidden"] = False
        save_config(cfg)
        icon.icon  = ICON_VISIBLE
        icon.title = "GameToggle - Jogos VISIVEIS"
        ctypes.windll.user32.MessageBeep(0)
    else:
        count = hide_games()
        cfg["hidden"] = True
        save_config(cfg)
        icon.icon  = ICON_HIDDEN
        icon.title = "GameToggle - Jogos OCULTOS"
        ctypes.windll.user32.MessageBeep(0)

def do_exit(icon, item):
    icon.stop()

def build_menu():
    return pystray.Menu(
        pystray.MenuItem("Alternar (Ocultar / Mostrar)", do_toggle, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Fechar GameToggle", do_exit),
    )
def alterar_game_mode_windows(ativar: bool):
    """Altera o Modo de Jogo utilizando comandos de política do sistema via PowerShell."""
    try:
        import subprocess
        valor = 1 if activar else 0
        
        # Comando que altera a política real que o Windows 10/11 lê atualmente
        comando_ps = (
            f"Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\GameBar' -Name 'AutoGameModeEnabled' -Value {valor}; "
            f"Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\GameBar' -Name 'AllowAutoGameMode' -Value {valor}; "
            # Força o serviço de configurações a atualizar a interface gráfica na hora
            f"Stop-Process -Name 'SystemSettings' -Force -ErrorAction SilentlyContinue"
        )
        
        subprocess.run(["powershell", "-Command", comando_ps], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        status = "ATIVADO" if activar else "DESATIVADO"
        print(f"[DEBUG] Modo de Jogo do Windows {status} via PowerShell.")
    except Exception as e:
        print(f"[DEBUG] Erro ao aplicar Modo de Jogo: {e}")

def do_toggle(icon, item=None):
    cfg = load_config()
    if cfg["hidden"]:
        count = show_games()
        cfg["hidden"] = False
        save_config(cfg)
        icon.icon  = ICON_VISIBLE
        icon.title = "GameToggle - Jogos VISIVEIS"
        
        # Desativa o Game Mode do Windows quando os jogos voltarem a aparecer
        alterar_game_mode_windows(ativar=False)
        
        ctypes.windll.user32.MessageBeep(0)
    else:
        count = hide_games()
        cfg["hidden"] = True
        save_config(cfg)
        icon.icon  = ICON_HIDDEN
        icon.title = "GameToggle - Jogos OCULTOS"
        
        # Ativa o Game Mode do Windows quando os jogos forem ocultados para jogar
        alterar_game_mode_windows(ativar=True)
        
        ctypes.windll.user32.MessageBeep(0)

def main():
    pythoncom.CoInitialize()  # inicializa COM uma vez
    ensure_dirs()
    start_watcher()

    cfg = load_config()
    initial_icon  = ICON_HIDDEN if cfg["hidden"] else ICON_VISIBLE
    initial_title = "GameToggle - Jogos OCULTOS" if cfg["hidden"] else "GameToggle - Jogos VISIVEIS"

    global tray_icon
    tray_icon = pystray.Icon(
        "GameToggle",
        initial_icon,
        initial_title,
        build_menu()
    )
    tray_icon.run()
    pythoncom.CoUninitialize()  # libera COM ao sair

if __name__ == "__main__":
    main()
