from os import path as os_path
import yaml


def loadTranslatePromptConfig(root_path: str | None = None, prompt_filename: str | None = None) -> dict:
    # PyInstaller 展開後
    if root_path and prompt_filename and os_path.exists(os_path.join(root_path, "_internal", "translation_settings", "prompt", prompt_filename)):
        prompt_path = os_path.join(root_path, "_internal", "translation_settings", "prompt", prompt_filename)
    # src-python 直下実行
    elif prompt_filename and os_path.exists(os_path.join(os_path.dirname(__file__), "models", "translation", "translation_settings", "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "models", "translation", "translation_settings", "prompt", prompt_filename)
    # translation フォルダ直下実行
    elif prompt_filename and os_path.exists(os_path.join(os_path.dirname(__file__), "translation_settings", "prompt", prompt_filename)):
        prompt_path = os_path.join(os_path.dirname(__file__), "translation_settings", "prompt", prompt_filename)
    else:
        raise FileNotFoundError(f"Prompt file not found: {prompt_filename}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
