"""
Unified language registry for ypack.

Provides a single source of truth for:
- Language metadata (canonical name, ISO code, description)
- Built-in translations for common installer UI strings
- Alias resolution for backward-compatible language names

This module is **framework-agnostic** — it contains NO installer-specific
(NSIS / WIX / Inno Setup) identifiers.  Framework-specific mappings live
in the corresponding converter module (e.g. ``converters/nsis_languages.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class LanguageInfo:
    """Metadata for a single language supported by the installer framework.

    This is a generic, framework-neutral record.  Installer-specific data
    (e.g. NSIS MUI name, LANG_* constant, LCID) is maintained separately
    in the converter layer — see ``converters/nsis_languages.py``.
    """

    name: str            # ypack canonical name (e.g., "SimplifiedChinese")
    iso_code: str        # ISO 639-1 / BCP 47 tag (e.g., "zh-CN")
    description: str     # Human-readable label (e.g., "Simplified Chinese")


# ---------------------------------------------------------------------------
# Language Registry — single source of truth
# ---------------------------------------------------------------------------

LANGUAGE_REGISTRY: Dict[str, LanguageInfo] = {}


def _reg(name: str, iso_code: str, desc: str = "") -> None:
    """Register a language in the global registry."""
    LANGUAGE_REGISTRY[name] = LanguageInfo(
        name=name,
        iso_code=iso_code,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Language Registry — core languages used by built-in translations
# Only languages that have entries in BUILTIN_TRANSLATIONS (and their
# immediate companions used by the codebase) are retained here to keep
# the registry compact and maintainable.
# ---------------------------------------------------------------------------
_reg("English",                "en",     "English (US)")
_reg("SimplifiedChinese",      "zh-CN",  "Simplified Chinese")
_reg("TraditionalChinese",     "zh-TW",  "Traditional Chinese")
_reg("French",                 "fr",     "French (France)")
_reg("German",                 "de",     "German (Germany)")
_reg("Spanish",                "es",     "Spanish (Spain)")
_reg("SpanishInternational",   "es-419", "Spanish (International)")
_reg("Portuguese",             "pt",     "Portuguese (Portugal)")
_reg("BrazilianPortuguese",    "pt-BR",  "Portuguese (Brazil)")
_reg("Italian",                "it",     "Italian (Italy)")
_reg("Dutch",                  "nl",     "Dutch (Netherlands)")
_reg("Polish",                 "pl",     "Polish (Poland)")
_reg("Czech",                  "cs",     "Czech (Czech Republic)")
_reg("Hungarian",              "hu",     "Hungarian (Hungary)")
_reg("Turkish",                "tr",     "Turkish (Turkey)")
_reg("Japanese",               "ja",     "Japanese (Japan)")
_reg("Korean",                 "ko",     "Korean (South Korea)")
_reg("Russian",                "ru",     "Russian (Russia)")
_reg("Swedish",                "sv",     "Swedish (Sweden)")
_reg("Norwegian",              "nb",     "Norwegian (Bokmål)")
_reg("NorwegianNynorsk",       "nn",     "Norwegian (Nynorsk)")
_reg("Danish",                 "da",     "Danish (Denmark)")
_reg("Ukrainian",              "uk",     "Ukrainian (Ukraine)")
_reg("Arabic",                 "ar",     "Arabic (Saudi Arabia)")
_reg("Thai",                   "th",     "Thai (Thailand)")
_reg("Vietnamese",             "vi",     "Vietnamese (Vietnam)")


# ---------------------------------------------------------------------------
# Alias map — maps legacy / shorthand names to canonical ypack names
# ---------------------------------------------------------------------------

_ALIAS_MAP: Dict[str, str] = {}


def _build_alias_map() -> None:
    """Build the alias map from the language registry."""
    # Canonical names (case-insensitive lookup)
    for name in LANGUAGE_REGISTRY:
        _ALIAS_MAP[name.lower()] = name

    # ISO code aliases
    for name, info in LANGUAGE_REGISTRY.items():
        _ALIAS_MAP[info.iso_code.lower()] = name

    # Legacy / shorthand aliases (case-insensitive, stored lowercase)
    _ALIAS_MAP.update({
        # Common aliases
        "chinese":              "SimplifiedChinese",
        "zh":                   "SimplifiedChinese",
        "zh-cn":                "SimplifiedChinese",
        "en":                   "English",
        "fr":                   "French",
        "de":                   "German",
        "es":                   "Spanish",
        "pt":                   "Portuguese",
        "pt-br":                "BrazilianPortuguese",
        "it":                   "Italian",
        "nl":                   "Dutch",
        "ja":                   "Japanese",
        "ko":                   "Korean",
        "ru":                   "Russian",
        "pl":                   "Polish",
        "tr":                   "Turkish",
        "ar":                   "Arabic",
        "he":                   "Hebrew",
        "uk":                   "Ukrainian",
        "vi":                   "Vietnamese",
        "th":                   "Thai",
        "fa":                   "Farsi",
        # NSIS MUI legacy aliases (so old configs still resolve)
        "simpchinese":          "SimplifiedChinese",
        "tradchinese":          "TraditionalChinese",
        "portuguesebr":         "BrazilianPortuguese",
    })


_build_alias_map()


def resolve_language_name(name: str) -> str:
    """Resolve a language name (possibly an alias) to the canonical ypack name.

    Case-insensitive.  Returns the input unchanged if no match is found
    (allows pass-through of unknown NSIS language names).

    Examples::

        >>> resolve_language_name("chinese")
        'SimplifiedChinese'
        >>> resolve_language_name("English")
        'English'
        >>> resolve_language_name("zh-CN")
        'SimplifiedChinese'
    """
    return _ALIAS_MAP.get(name.lower(), name)


def get_language_info(name: str) -> Optional[LanguageInfo]:
    """Look up language info by canonical name or alias.

    Returns ``None`` if the language is not in the registry (the caller
    should decide how to handle unrecognised languages).
    """
    canonical = resolve_language_name(name)
    return LANGUAGE_REGISTRY.get(canonical)


# ---------------------------------------------------------------------------
# Built-in UI string translations
# ---------------------------------------------------------------------------

# String IDs used in the generated NSIS installer UI.
# Users may override any of these in the YAML ``languages[].strings`` map.
BUILTIN_STRING_IDS = (
    "shortcuts_desktop",
    "shortcuts_startmenu",
    "langpage_title",
    "langpage_desc",
    "finish_run",
) 

# {canonical_language_name: {string_id: translation}}
BUILTIN_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "English": {
        "shortcuts_desktop":    "Create desktop shortcut",
        "shortcuts_startmenu":  "Create start menu shortcut",
        "langpage_title":       "Choose installation language",
        "langpage_desc":        "Select which language the installer should use.",
        "finish_run":           "Run ${APP_NAME}",
    },
    "SimplifiedChinese": {
        "shortcuts_desktop":    "创建桌面快捷方式",
        "shortcuts_startmenu":  "创建开始菜单快捷方式",
        "langpage_title":       "选择安装语言",
        "langpage_desc":        "请选择安装程序使用的语言。",
        "finish_run":           "运行 ${APP_NAME}",
    },
    "TraditionalChinese": {
        "shortcuts_desktop":    "建立桌面捷徑",
        "shortcuts_startmenu":  "建立開始功能表捷徑",
        "langpage_title":       "選擇安裝語言",
        "langpage_desc":        "請選擇安裝程式使用的語言。",
        "finish_run":           "執行 ${APP_NAME}",
    },
    "French": {
        "shortcuts_desktop":    "Créer un raccourci sur le bureau",
        "shortcuts_startmenu":  "Créer un raccourci dans le menu Démarrer",
        "langpage_title":       "Choisir la langue d'installation",
        "langpage_desc":        "Sélectionnez la langue du programme d'installation.",
        "finish_run":           "Lancer ${APP_NAME}",
    },
    "German": {
        "shortcuts_desktop":    "Desktop-Verknüpfung erstellen",
        "shortcuts_startmenu":  "Startmenü-Verknüpfung erstellen",
        "langpage_title":       "Installationssprache wählen",
        "langpage_desc":        "Wählen Sie die Sprache des Installationsprogramms.",
        "finish_run":           "${APP_NAME} starten",
    },
    "Spanish": {
        "shortcuts_desktop":    "Crear acceso directo en el escritorio",
        "shortcuts_startmenu":  "Crear acceso directo en el menú Inicio",
        "langpage_title":       "Elegir idioma de instalación",
        "langpage_desc":        "Seleccione el idioma del instalador.",
        "finish_run":           "Ejecutar ${APP_NAME}",
    },
    "Japanese": {
        "shortcuts_desktop":    "デスクトップショートカットを作成",
        "shortcuts_startmenu":  "スタートメニューショートカットを作成",
        "langpage_title":       "インストール言語の選択",
        "langpage_desc":        "インストーラーの言語を選択してください。",
        "finish_run":           "${APP_NAME} を実行",
    },
    "Korean": {
        "shortcuts_desktop":    "바탕화면 바로 가기 만들기",
        "shortcuts_startmenu":  "시작 메뉴 바로 가기 만들기",
        "langpage_title":       "설치 언어 선택",
        "langpage_desc":        "설치 프로그램에서 사용할 언어를 선택하십시오.",
        "finish_run":           "${APP_NAME} 실행",
    },
    "Russian": {
        "shortcuts_desktop":    "Создать ярлык на рабочем столе",
        "shortcuts_startmenu":  "Создать ярлык в меню «Пуск»",
        "langpage_title":       "Выберите язык установки",
        "langpage_desc":        "Выберите язык программы установки.",
        "finish_run":           "Запустить ${APP_NAME}",
    },
    "Portuguese": {
        "shortcuts_desktop":    "Criar atalho na área de trabalho",
        "shortcuts_startmenu":  "Criar atalho no menu Iniciar",
        "langpage_title":       "Escolher idioma de instalação",
        "langpage_desc":        "Selecione o idioma do instalador.",
        "finish_run":           "Executar ${APP_NAME}",
    },
    "BrazilianPortuguese": {
        "shortcuts_desktop":    "Criar atalho na área de trabalho",
        "shortcuts_startmenu":  "Criar atalho no menu Iniciar",
        "langpage_title":       "Escolher idioma de instalação",
        "langpage_desc":        "Selecione o idioma do instalador.",
        "finish_run":           "Executar ${APP_NAME}",
    },
    "Italian": {
        "shortcuts_desktop":    "Crea collegamento sul desktop",
        "shortcuts_startmenu":  "Crea collegamento nel menu Start",
        "langpage_title":       "Scegli la lingua di installazione",
        "langpage_desc":        "Seleziona la lingua del programma di installazione.",
        "finish_run":           "Esegui ${APP_NAME}",
    },
    "Dutch": {
        "shortcuts_desktop":    "Snelkoppeling op bureaublad maken",
        "shortcuts_startmenu":  "Snelkoppeling in Startmenu maken",
        "langpage_title":       "Installatietaal kiezen",
        "langpage_desc":        "Selecteer de taal van het installatieprogramma.",
        "finish_run":           "${APP_NAME} starten",
    },
    "Polish": {
        "shortcuts_desktop":    "Utwórz skrót na pulpicie",
        "shortcuts_startmenu":  "Utwórz skrót w menu Start",
        "langpage_title":       "Wybierz język instalacji",
        "langpage_desc":        "Wybierz język programu instalacyjnego.",
        "finish_run":           "Uruchom ${APP_NAME}",
    },
    "Turkish": {
        "shortcuts_desktop":    "Masaüstü kısayolu oluştur",
        "shortcuts_startmenu":  "Başlat menüsü kısayolu oluştur",
        "langpage_title":       "Kurulum dilini seçin",
        "langpage_desc":        "Yükleyicinin kullanacağı dili seçin.",
        "finish_run":           "${APP_NAME} çalıştır",
    },
    "Czech": {
        "shortcuts_desktop":    "Vytvořit zástupce na ploše",
        "shortcuts_startmenu":  "Vytvořit zástupce v nabídce Start",
        "langpage_title":       "Zvolte jazyk instalace",
        "langpage_desc":        "Vyberte jazyk instalačního programu.",
        "finish_run":           "Spustit ${APP_NAME}",
    },
    "Hungarian": {

        "shortcuts_desktop":    "Asztali parancsikon létrehozása",
        "shortcuts_startmenu":  "Start menü parancsikon létrehozása",
        "langpage_title":       "Telepítési nyelv kiválasztása",
        "langpage_desc":        "Válassza ki a telepítő nyelvét.",
        "finish_run":           "${APP_NAME} indítása",
    },
    "Swedish": {
        "shortcuts_desktop":    "Skapa genväg på skrivbordet",
        "shortcuts_startmenu":  "Skapa genväg i Start-menyn",
        "langpage_title":       "Välj installationsspråk",
        "langpage_desc":        "Välj språk för installationsprogrammet.",
        "finish_run":           "Starta ${APP_NAME}",
    },
    "Norwegian": {
        "shortcuts_desktop":    "Opprett snarvei på skrivebordet",
        "shortcuts_startmenu":  "Opprett snarvei i Start-menyen",
        "langpage_title":       "Velg installasjonsspråk",
        "langpage_desc":        "Velg språket installasjonsprogrammet skal bruke.",
        "finish_run":           "Kjør ${APP_NAME}",
    },
    "Danish": {
        "shortcuts_desktop":    "Opret genvej på skrivebordet",
        "shortcuts_startmenu":  "Opret genvej i Start-menuen",
        "langpage_title":       "Vælg installationssprog",
        "langpage_desc":        "Vælg det sprog, installationsprogrammet skal bruge.",
        "finish_run":           "Kør ${APP_NAME}",
    },
    "Ukrainian": {
        "shortcuts_desktop":    "Створити ярлик на робочому столі",
        "shortcuts_startmenu":  "Створити ярлик у меню «Пуск»",
        "langpage_title":       "Оберіть мову встановлення",
        "langpage_desc":        "Оберіть мову програми встановлення.",
        "finish_run":           "Запустити ${APP_NAME}",
    },
    "Arabic": {
        "shortcuts_desktop":    "إنشاء اختصار على سطح المكتب",
        "shortcuts_startmenu":  "إنشاء اختصار في قائمة ابدأ",
        "langpage_title":       "اختر لغة التثبيت",
        "langpage_desc":        "حدد اللغة التي يستخدمها برنامج التثبيت.",
        "finish_run":           "تشغيل ${APP_NAME}",
    },
    "Thai": {
        "shortcuts_desktop":    "สร้างทางลัดบนเดสก์ท็อป",
        "shortcuts_startmenu":  "สร้างทางลัดในเมนูเริ่ม",
        "langpage_title":       "เลือกภาษาในการติดตั้ง",
        "langpage_desc":        "เลือกภาษาที่ตัวติดตั้งจะใช้",
        "finish_run":           "เรียกใช้ ${APP_NAME}",
    },
    "Vietnamese": {
        "shortcuts_desktop":    "Tạo lối tắt trên màn hình",
        "shortcuts_startmenu":  "Tạo lối tắt trong menu Bắt đầu",
        "langpage_title":       "Chọn ngôn ngữ cài đặt",
        "langpage_desc":        "Chọn ngôn ngữ cho trình cài đặt.",
        "finish_run":           "Chạy ${APP_NAME}",
    },
}

# Copy Spanish to SpanishInternational
BUILTIN_TRANSLATIONS["SpanishInternational"] = BUILTIN_TRANSLATIONS["Spanish"].copy()
# Copy Norwegian to NorwegianNynorsk
BUILTIN_TRANSLATIONS["NorwegianNynorsk"] = BUILTIN_TRANSLATIONS["Norwegian"].copy()


def get_translated_string(
    lang_name: str,
    string_id: str,
    user_strings: Optional[Dict[str, str]] = None,
) -> str:
    """Get a translated string for a language.

    Lookup order:
      1. User-provided strings (from YAML ``languages[].strings``)
      2. Built-in translations for the (canonical) language
      3. English fallback

    Args:
        lang_name: Canonical ypack language name (or alias — will be resolved).
        string_id: String identifier (e.g., ``"shortcuts_page_title"``).
        user_strings: Optional user-defined string overrides from YAML.

    Returns:
        Translated string, or English fallback.
        Returns empty string if not found anywhere.
    """
    # 1. User override
    if user_strings and string_id in user_strings:
        return user_strings[string_id]

    # 2. Built-in translation for this language
    canonical = resolve_language_name(lang_name)
    if canonical in BUILTIN_TRANSLATIONS:
        text = BUILTIN_TRANSLATIONS[canonical].get(string_id)
        if text is not None:
            return text

    # 3. English fallback
    return BUILTIN_TRANSLATIONS.get("English", {}).get(string_id, "")
