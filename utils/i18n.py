import json
import os


LOCALE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales")


class I18n:
    def __init__(self, locale_dir=LOCALE_DIR):
        self.locale_dir = locale_dir
        self._cache = {}

    def _load(self, lang):
        if lang not in self._cache:
            path = os.path.join(self.locale_dir, f"{lang}.json")
            if not os.path.exists(path):
                lang = "es"
                path = os.path.join(self.locale_dir, f"{lang}.json")
            with open(path, "r", encoding="utf-8") as f:
                self._cache[lang] = json.load(f)
        return self._cache[lang]

    def t(self, lang, key, **kwargs):
        if not lang or lang not in ("es", "en", "pt"):
            lang = "es"
        locale = self._load(lang)
        keys = key.split(".")
        val = locale
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                val = None
            if val is None:
                return self._fallback(key, keys, kwargs)
        if isinstance(val, str):
            return val.format(**kwargs)
        return val

    def _fallback(self, key, keys, kwargs):
        try:
            locale = self._load("es")
            val = locale
            for k in keys:
                if isinstance(val, dict):
                    val = val.get(k)
                else:
                    return key
                if val is None:
                    return key
            if isinstance(val, str):
                return val.format(**kwargs)
            return str(val)
        except:
            return key

    def reload(self, lang=None):
        if lang:
            self._cache.pop(lang, None)
        else:
            self._cache.clear()
