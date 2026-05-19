import ctypes
from ctypes import wintypes
import json
import os
import shutil
import subprocess
import winreg
from pathlib import Path
from collections import Counter

from PyQt5.QtCore import QFileInfo, QSize, QUrl, Qt
from PyQt5.QtGui import QColor, QIcon, QPixmap, QImage
from PyQt5.QtWidgets import QFileIconProvider


def load_json_file(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False


def get_desktop_path():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        desktop_path = winreg.QueryValueEx(key, "Desktop")[0]
        winreg.CloseKey(key)
        return Path(desktop_path)
    except Exception:
        return Path.home() / "Desktop"


def get_wallpaper_path():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Desktop"
        )

        try:
            wallpaper_path, _ = winreg.QueryValueEx(key, "Wallpaper")
            wallpaper_path = os.path.expandvars(wallpaper_path)
            if wallpaper_path and os.path.exists(wallpaper_path):
                return wallpaper_path
        except Exception:
            pass

        try:
            transcoded_path, _ = winreg.QueryValueEx(key, "TranscodedWallpaper")
            transcoded_path = os.path.expandvars(transcoded_path)
            if transcoded_path and os.path.exists(transcoded_path):
                return transcoded_path

            if transcoded_path:
                nombre_archivo = os.path.basename(transcoded_path)
                temas_path = Path(os.environ.get('APPDATA', '')) / "Microsoft" / "Windows" / "Themes"
                transcoded_file = temas_path / nombre_archivo
                if transcoded_file.exists():
                    return str(transcoded_file)
                transcoded_wallpaper = temas_path / "TranscodedWallpaper"
                if transcoded_wallpaper.exists():
                    return str(transcoded_wallpaper)
        except Exception:
            pass

        try:
            wallpaper_path, _ = winreg.QueryValueEx(key, "Wallpaper")
            wallpaper_path = os.path.expandvars(wallpaper_path)
            if wallpaper_path:
                nombre_archivo = os.path.basename(wallpaper_path)
                appdata_path = Path(os.environ.get('APPDATA', '')) / "Microsoft" / "Windows" / "Themes" / nombre_archivo
                if appdata_path.exists():
                    return str(appdata_path)
                windows_path = Path(os.environ.get('WINDIR', '')) / "Web" / "Wallpaper" / nombre_archivo
                if windows_path.exists():
                    return str(windows_path)
                wallpaper_base = Path(os.environ.get('WINDIR', '')) / "Web" / "Wallpaper"
                if wallpaper_base.exists():
                    for subfolder in wallpaper_base.iterdir():
                        if subfolder.is_dir():
                            candidate = subfolder / nombre_archivo
                            if candidate.exists():
                                return str(candidate)
        except Exception:
            pass
    except Exception:
        pass

    try:
        temas_path = Path(os.environ.get('APPDATA', '')) / "Microsoft" / "Windows" / "Themes"
        if temas_path.exists():
            transcoded_wallpaper = temas_path / "TranscodedWallpaper"
            if transcoded_wallpaper.exists() and transcoded_wallpaper.is_file():
                return str(transcoded_wallpaper)
            for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.jfif']:
                for archivo in temas_path.glob(f'*{ext}'):
                    if archivo.is_file() and archivo.stat().st_size > 0:
                        return str(archivo)
    except Exception:
        pass

    try:
        wallpaper_base = Path(os.environ.get('WINDIR', '')) / "Web" / "Wallpaper"
        if wallpaper_base.exists():
            for subfolder in wallpaper_base.iterdir():
                if subfolder.is_dir():
                    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.jfif']:
                        for archivo in subfolder.glob(f'*{ext}'):
                            if archivo.is_file() and archivo.stat().st_size > 0:
                                return str(archivo)
    except Exception:
        pass

    return None


def analyze_image_colors(image_path, num_colors=5):
    try:
        image = QImage(str(image_path))
        if image.isNull():
            return None

        if image.width() > 200 or image.height() > 200:
            image = image.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        colors = []
        for y in range(0, image.height(), 5):
            for x in range(0, image.width(), 5):
                color = QColor(image.pixel(x, y))
                if 30 < color.lightness() < 225:
                    colors.append((color.red(), color.green(), color.blue()))

        if not colors:
            return None

        count = Counter(colors)
        return [item[0] for item in count.most_common(num_colors)]
    except Exception:
        return None


def generate_color_palette(dominant_colors):
    if not dominant_colors:
        return {
            'fondo': (100, 150, 200, 140),
            'borde': (50, 100, 150, 220),
            'boton_expandir': (70, 110, 150, 200),
            'texto': (255, 255, 255, 255),
            'lista_fondo': (60, 100, 140, 120),
            'lista_borde': (80, 120, 160, 180)
        }

    r_base, g_base, b_base = dominant_colors[0]
    luminosity = r_base * 0.299 + g_base * 0.587 + b_base * 0.114

    if luminosity < 50:
        r_base = min(255, int(r_base * 1.3))
        g_base = min(255, int(g_base * 1.3))
        b_base = min(255, int(b_base * 1.3))
    elif luminosity > 200:
        r_base = max(0, int(r_base * 0.7))
        g_base = max(0, int(g_base * 0.7))
        b_base = max(0, int(b_base * 0.7))

    luminosity = r_base * 0.299 + g_base * 0.587 + b_base * 0.114
    a_fondo = 160 if luminosity < 100 else 180 if luminosity > 180 else 140
    fondo = (r_base, g_base, b_base, a_fondo)

    borde = (max(0, min(255, int(r_base * 0.65))), max(0, min(255, int(g_base * 0.65))), max(0, min(255, int(b_base * 0.65))), 220)
    boton_expandir = (max(0, min(255, int(r_base * 0.75))), max(0, min(255, int(g_base * 0.75))), max(0, min(255, int(b_base * 0.75))), 200)
    texto = (255, 255, 255, 255) if luminosity < 120 else (30, 30, 30, 255)
    lista_fondo = (max(0, min(255, int(r_base * 0.55))), max(0, min(255, int(g_base * 0.55))), max(0, min(255, int(b_base * 0.55))), 120)
    lista_borde = (max(0, min(255, int(r_base * 0.7))), max(0, min(255, int(g_base * 0.7))), max(0, min(255, int(b_base * 0.7))), 180)

    return {
        'fondo': fondo,
        'borde': borde,
        'boton_expandir': boton_expandir,
        'texto': texto,
        'lista_fondo': lista_fondo,
        'lista_borde': lista_borde
    }


def extract_icon_from_file_path(path, index=0):
    """Extrae el icono desde un ejecutable/dll/ico usando ExtractIconEx."""
    if not path or not os.path.exists(path):
        return None

    lower_path = str(path).lower()
    if lower_path.endswith('.ico'):
        try:
            return QIcon(path)
        except Exception:
            return None

    try:
        large_icons = (wintypes.HICON * 1)()
        small_icons = (wintypes.HICON * 1)()
        extracted = ctypes.windll.shell32.ExtractIconExW(
            str(path),
            int(index),
            large_icons,
            small_icons,
            1
        )
        if extracted > 0 and small_icons[0]:
            try:
                if hasattr(QPixmap, 'fromWinHICON'):
                    pixmap = QPixmap.fromWinHICON(small_icons[0])
                    ctypes.windll.user32.DestroyIcon(small_icons[0])
                    if not pixmap.isNull():
                        return QIcon(pixmap)
            except Exception:
                ctypes.windll.user32.DestroyIcon(small_icons[0])
    except Exception:
        pass

    return None


def get_shell_icon_location(path):
    """Obtiene la ubicación del icono desde el Shell de Windows."""
    if not path:
        return None, 0

    SHGFI_ICONLOCATION = 0x000001000
    SHGFI_USEFILEATTRIBUTES = 0x000000010

    class SHFILEINFO(ctypes.Structure):
        _fields_ = [
            ("hIcon", wintypes.HICON),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", wintypes.WCHAR * 260),
            ("szTypeName", wintypes.WCHAR * 80),
        ]

    shfi = SHFILEINFO()
    flags = SHGFI_ICONLOCATION | SHGFI_USEFILEATTRIBUTES

    try:
        result = ctypes.windll.shell32.SHGetFileInfoW(
            str(path),
            0,
            ctypes.byref(shfi),
            ctypes.sizeof(shfi),
            flags
        )
        if result:
            icon_path = shfi.szDisplayName
            if icon_path:
                icon_path = icon_path.strip()
                icon_index = 0
                if ',' in icon_path:
                    icon_path, icon_index_str = icon_path.rsplit(',', 1)
                    icon_path = icon_path.strip()
                    try:
                        icon_index = int(icon_index_str)
                    except ValueError:
                        icon_index = 0
                return icon_path, icon_index
    except Exception:
        pass

    return None, 0


def get_shell_icon(path):
    """Obtiene el icono real del Shell de Windows para un archivo."""
    if not path:
        return None

    icon_location, icon_index = get_shell_icon_location(path)
    if icon_location:
        icon = extract_icon_from_file_path(icon_location, icon_index)
        if icon:
            return icon

    SHGFI_ICON = 0x000000100
    SHGFI_SMALLICON = 0x000000001

    class SHFILEINFO(ctypes.Structure):
        _fields_ = [
            ("hIcon", wintypes.HICON),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", wintypes.WCHAR * 260),
            ("szTypeName", wintypes.WCHAR * 80),
        ]

    shfi = SHFILEINFO()
    flags = SHGFI_ICON | SHGFI_SMALLICON

    try:
        result = ctypes.windll.shell32.SHGetFileInfoW(
            str(path),
            0,
            ctypes.byref(shfi),
            ctypes.sizeof(shfi),
            flags
        )
        if result and shfi.hIcon:
            try:
                if hasattr(QPixmap, 'fromWinHICON'):
                    pixmap = QPixmap.fromWinHICON(shfi.hIcon)
                    ctypes.windll.user32.DestroyIcon(shfi.hIcon)
                    if not pixmap.isNull():
                        return QIcon(pixmap)
            except Exception:
                ctypes.windll.user32.DestroyIcon(shfi.hIcon)
    except Exception:
        pass

    return None


def get_icon_from_url_file(url_path, icon_provider=None):
    if icon_provider is None:
        icon_provider = QFileIconProvider()

    file_info = QFileInfo(str(url_path))
    icon = icon_provider.icon(file_info)
    if icon and not icon.isNull():
        return icon

    try:
        icon_file = None
        icon_index = 0
        with open(url_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                lower_line = line.lower()
                if lower_line.startswith('iconfile='):
                    icon_file = line.split('=', 1)[1].strip().strip('"')
                elif lower_line.startswith('iconindex='):
                    try:
                        icon_index = int(line.split('=', 1)[1].strip())
                    except ValueError:
                        icon_index = 0

        if icon_file:
            raw_value = icon_file
            if ',' in raw_value:
                raw_value, index_part = raw_value.split(',', 1)
                raw_value = raw_value.strip()
                try:
                    icon_index = int(index_part.strip())
                except ValueError:
                    icon_index = 0

            icon_file = raw_value.strip()
            icon_file = icon_file.strip('"')
            icon_file = os.path.expandvars(icon_file)

            if not os.path.isabs(icon_file):
                icon_file = os.path.normpath(
                    os.path.join(os.path.dirname(str(url_path)), icon_file)
                )

            if os.path.exists(icon_file):
                if icon_file.lower().endswith('.ico'):
                    try:
                        return QIcon(icon_file)
                    except Exception:
                        pass

                icon = extract_icon_from_file_path(icon_file, icon_index)
                if icon:
                    return icon

                info = QFileInfo(icon_file)
                icon = icon_provider.icon(info)
                if icon and not icon.isNull():
                    return icon

            # Si la ruta extraída apunta a un ejecutable o dll, intentar extraer directamente
            if icon_file.lower().endswith(('.exe', '.dll')) and os.path.isfile(icon_file):
                icon = extract_icon_from_file_path(icon_file, icon_index)
                if icon:
                    return icon

        # Fallback: intentar obtener la ubicación del icono desde el Shell y extraerlo
        shell_icon_path, shell_icon_index = get_shell_icon_location(url_path)
        if shell_icon_path:
            shell_icon_path = shell_icon_path.strip('"')
            shell_icon_path = os.path.expandvars(shell_icon_path)
            if not os.path.isabs(shell_icon_path):
                shell_icon_path = os.path.normpath(
                    os.path.join(os.path.dirname(str(url_path)), shell_icon_path)
                )
            shell_icon = extract_icon_from_file_path(shell_icon_path, shell_icon_index)
            if shell_icon:
                return shell_icon
    except Exception:
        pass

    return None


def get_file_icon(path, icon_provider=None, size=24, resolution_multiplier=2.0):
    if icon_provider is None:
        icon_provider = QFileIconProvider()

    ruta = str(path)
    if ruta.lower().endswith('.url'):
        icon = get_icon_from_url_file(ruta, icon_provider)
        if icon:
            return icon

        # Fallback adicional: intentar extraer icono directamente desde el shell
        icon = extract_icon_from_file_path(ruta, 0)
        if icon:
            return icon

    try:
        file_info = QFileInfo(ruta)
        icon = icon_provider.icon(file_info)
        if icon and not icon.isNull():
            return icon
    except Exception:
        pass

    shell_icon = get_shell_icon(ruta)
    if shell_icon:
        return shell_icon

    return icon_provider.icon(QFileIconProvider.File)


def move_with_collision(source, destination_folder, max_attempts=1000):
    source_path = Path(source)
    destination_folder = Path(destination_folder)
    destination_folder.mkdir(parents=True, exist_ok=True)
    destination = destination_folder / source_path.name
    counter = 1

    if source_path.is_file():
        base_name = source_path.stem
        extension = source_path.suffix
        while destination.exists() and counter <= max_attempts:
            destination = destination_folder / f"{base_name}_{counter}{extension}"
            counter += 1
    else:
        base_name = source_path.name
        while destination.exists() and counter <= max_attempts:
            destination = destination_folder / f"{base_name}_{counter}"
            counter += 1

    if destination.exists():
        raise FileExistsError("No se pudo mover el archivo porque ya existen demasiadas versiones")

    shutil.move(str(source_path), str(destination))
    return destination
