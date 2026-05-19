import json
from pathlib import Path

DEFAULT_CONFIG = {
    "casillas": {},
    "tamanos": {},
    "tamanos_iconos": {},
    "tipos_vista": {},
    "estados": {},
    "configuraciones": {},
    "colores": {},
    "panel": None
}


class PersistenceManager:
    def __init__(self, base_folder=None):
        self.base_folder = Path(base_folder) if base_folder else Path.home() / "Desktop" / "Organizador_Casillas"
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.config_file = self.base_folder / ".posiciones.json"
        self.data = self._load()

    def _load(self):
        if not self.config_file.exists():
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return DEFAULT_CONFIG.copy()

        for key, value in DEFAULT_CONFIG.items():
            data.setdefault(key, value)
        return data

    def save(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception:
            return False

    def get_position(self, name):
        value = self.data.get("casillas", {}).get(name)
        return tuple(value) if isinstance(value, list) and len(value) == 2 else None

    def set_position(self, name, x, y):
        self.data.setdefault("casillas", {})[name] = [x, y]
        self.save()

    def set_panel_position(self, x, y):
        self.data["panel"] = [x, y]
        self.save()

    def remove_casilla(self, name):
        for key in ["casillas", "tamanos", "tamanos_iconos", "tipos_vista", "estados"]:
            if name in self.data.get(key, {}):
                del self.data[key][name]
        self.save()

    def get_tamano_info(self, name):
        tamanos = self.data.get("tamanos", {}).get(name)
        if isinstance(tamanos, dict):
            colapsado = tuple(tamanos.get("colapsado")) if tamanos.get("colapsado") else None
            expandido = tuple(tamanos.get("expandido")) if tamanos.get("expandido") else None
            return colapsado, expandido
        if isinstance(tamanos, list) and len(tamanos) == 2:
            return tuple(tamanos), None
        return None, None

    def set_tamano_info(self, name, size, expanded=False):
        self.data.setdefault("tamanos", {}).setdefault(name, {})
        key = "expandido" if expanded else "colapsado"
        self.data["tamanos"][name][key] = [size[0], size[1]]
        self.save()

    def get_icon_size(self, name):
        value = self.data.get("tamanos_iconos", {}).get(name)
        return value if isinstance(value, int) else None

    def set_icon_size(self, name, size):
        self.data.setdefault("tamanos_iconos", {})[name] = size
        self.save()

    def get_view_type(self, name):
        value = self.data.get("tipos_vista", {}).get(name)
        return value if isinstance(value, str) else None

    def set_view_type(self, name, view_type):
        self.data.setdefault("tipos_vista", {})[name] = view_type
        self.save()

    def get_config(self, key, default=None):
        return self.data.get("configuraciones", {}).get(key, default)

    def set_config(self, key, value):
        self.data.setdefault("configuraciones", {})[key] = value
        self.save()

    def get_colors(self):
        return self.data.get("colores", {})

    def set_colors(self, colors):
        self.data["colores"] = {k: list(v) for k, v in colors.items()}
        self.save()
