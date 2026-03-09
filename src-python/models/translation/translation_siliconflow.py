from openai import OpenAI
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import re
import logging
import time

try:
    from .translation_languages import translation_lang
    from .translation_utils import loadTranslatePromptConfig
except Exception:
    import sys
    from os import path as os_path
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang, loadTranslationLanguages
    from translation_utils import loadTranslatePromptConfig
    translation_lang = loadTranslationLanguages(path=".", force=True)

sf_logger = logging.getLogger("siliconflow")
sf_logger.setLevel(logging.DEBUG)

def _setup_sf_logger(log_dir: str = None):
    """Set up file handler for SiliconFlow logger if not already configured.

    Writes to both siliconflow.log (detailed) and process.log (info-level)
    so API call records are visible in the main log file.
    """
    if sf_logger.handlers:
        return
    try:
        import os
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, "siliconflow.log")
        else:
            log_path = "siliconflow.log"
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        sf_logger.addHandler(handler)

        # Also mirror INFO+ messages to process.log so users can see API records
        process_log_path = os.path.join(log_dir, "..", "process.log") if log_dir else "process.log"
        process_log_path = os.path.normpath(process_log_path)
        from logging.handlers import RotatingFileHandler
        process_handler = RotatingFileHandler(
            process_log_path, maxBytes=10*1024*1024, backupCount=1, encoding="utf-8", delay=True
        )
        process_handler.setLevel(logging.INFO)
        process_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        sf_logger.addHandler(process_handler)
    except Exception:
        pass

def _authentication_check(api_key: str) -> bool:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1",
            timeout=30,
        )
        client.models.list()
        return True
    except Exception:
        return False

def _get_available_text_models(api_key: str) -> list[str]:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.siliconflow.cn/v1",
        timeout=30,
    )
    res = client.models.list()
    allowed_models = []

    for model in res.data:
        model_id = model.id

        exclude_keywords = [
            "whisper",
            "embedding",
            "image",
            "tts",
            "audio",
            "search",
            "transcribe",
            "diarize",
            "vision",
            "rerank",
            "stable-diffusion",
            "flux",
            "vl",
        ]

        if any(kw in model_id.lower() for kw in exclude_keywords):
            continue

        allowed_models.append(model_id)

    allowed_models.sort()
    return allowed_models

class SiliconFlowClient:
    """SiliconFlow API Translation wrapper using OpenAI-compatible endpoint.

    SiliconFlow provides LLM inference with an OpenAI-compatible API.
    API endpoint: https://api.siliconflow.cn/v1
    Docs: https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions
    """
    def __init__(self, root_path: str = None):
        self.api_key = None
        self.model = None
        self.base_url = "https://api.siliconflow.cn/v1"

        # Set up logging
        log_dir = None
        if root_path:
            import os
            log_dir = os.path.join(root_path, "logs")
        _setup_sf_logger(log_dir)

        # Model parameters
        self.enable_asr_correction = False
        self.enable_thinking = False
        self.max_tokens = 1024
        self.temperature = 0.4
        self.custom_system_prompt = ""

        prompt_config = loadTranslatePromptConfig(root_path, "translation_siliconflow.yml")
        self.supported_languages = list(translation_lang["SiliconFlow_API"]["source"].keys())
        self.prompt_template = prompt_config["system_prompt"]
        self.prompt_template_asr_correction = prompt_config.get("system_prompt_asr_correction", self.prompt_template)
        self.history_cfg = prompt_config.get("history", {
            "use_history": False,
            "sources": [],
            "max_messages": 0,
            "max_chars": 0,
            "header_template": "",
            "item_template": "[{source}] {role}: {text}",
        })
        self._context_history: list[dict] = []
        self.last_corrected_source: str = ""

        self.siliconflow_llm = None

    def getModelList(self) -> list[str]:
        return _get_available_text_models(self.api_key) if self.api_key else []

    def getAuthKey(self) -> str:
        return self.api_key

    def setAuthKey(self, api_key: str) -> bool:
        result = _authentication_check(api_key)
        if result:
            self.api_key = api_key
            sf_logger.info(f"[SiliconFlow] Auth successful, key=...{api_key[-6:]}")
        else:
            sf_logger.warning(f"[SiliconFlow] Auth failed")
        return result

    def getModel(self) -> str:
        return self.model

    def setModel(self, model: str) -> bool:
        if model in self.getModelList():
            self.model = model
            return True
        else:
            return False

    def updateClient(self) -> None:
        top_p_value = 0.95 if self.enable_thinking else 0.9
        self.siliconflow_llm = ChatOpenAI(
            base_url=self.base_url,
            model=self.model,
            api_key=SecretStr(self.api_key),
            streaming=False,
            max_tokens=self.max_tokens if self.max_tokens > 0 else None,
            temperature=self.temperature,
            top_p=top_p_value,
            request_timeout=60,
            max_retries=0,
        )
        sf_logger.info(f"[SiliconFlow] Client updated: model={self.model} thinking={self.enable_thinking} asr_correction={self.enable_asr_correction} temp={self.temperature} max_tokens={self.max_tokens} top_p={top_p_value}")

    def setContextHistory(self, history_items: list[dict]) -> None:
        self._context_history = history_items or []

    def translate(self, text: str, input_lang: str, output_lang: str) -> str:
        self.last_corrected_source = ""
        if self.custom_system_prompt:
            template = self.custom_system_prompt
        elif self.enable_asr_correction:
            template = self.prompt_template_asr_correction
        else:
            template = self.prompt_template
        system_prompt = template.format(
            supported_languages=self.supported_languages,
            input_lang=input_lang,
            output_lang=output_lang,
        )

        if self.history_cfg.get("use_history"):
            allowed_sources = set(self.history_cfg.get("sources", []))
            max_messages = int(self.history_cfg.get("max_messages", 0))
            max_chars = int(self.history_cfg.get("max_chars", 0))
            item_tmpl = self.history_cfg.get("item_template", "[{source}] {role}: {text}")
            header_tmpl = self.history_cfg.get("header_template", "{history}")

            filtered = [h for h in self._context_history if h.get("source") in allowed_sources]
            recent = filtered[-max_messages:] if max_messages > 0 else filtered
            formatted_items = []
            for h in recent:
                timestamp_str = ''
                if 'timestamp' in h:
                    from datetime import datetime
                    try:
                        ts = datetime.fromisoformat(h['timestamp'])
                        timestamp_str = ts.strftime('%H:%M')
                    except Exception:
                        timestamp_str = ''
                formatted_items.append(
                    item_tmpl.format(
                        timestamp=timestamp_str,
                        source=h.get("source", ""),
                        role=h.get("role", ""),
                        text=h.get("text", ""),
                    )
                )
            history_blob = "\n".join(formatted_items).strip()
            if max_chars and len(history_blob) > max_chars:
                history_blob = history_blob[-max_chars:]
            history_header = header_tmpl.format(max_messages=max_messages, history=history_blob)
            if history_header:
                system_prompt = f"{system_prompt}\n\n{history_header}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        sf_logger.info(f"[SiliconFlow Request] model={self.model} thinking={self.enable_thinking} asr_correction={self.enable_asr_correction} temp={self.temperature} max_tokens={self.max_tokens}")
        sf_logger.debug(f"[SiliconFlow Prompt] system={system_prompt[:200]}...")
        sf_logger.debug(f"[SiliconFlow Input] text={text}")

        start_time = time.time()
        resp = self.siliconflow_llm.invoke(messages)
        elapsed = time.time() - start_time

        content = ""
        if isinstance(resp.content, str):
            content = resp.content
        elif isinstance(resp.content, list):
            for part in resp.content:
                if isinstance(part, str):
                    content += part
                elif isinstance(part, dict) and "content" in part and isinstance(part["content"], str):
                    content += part["content"]
        content = content.strip()

        sf_logger.info(f"[SiliconFlow Response] elapsed={elapsed:.2f}s len={len(content)}")
        sf_logger.debug(f"[SiliconFlow Output Raw] content={content[:500]}")

        # Strip <think>...</think> tags (reasoning tokens from thinking models like DeepSeek-R1)
        think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL)
        if think_match:
            sf_logger.debug(f"[SiliconFlow Think] thinking={think_match.group(1).strip()[:300]}")
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            sf_logger.info(f"[SiliconFlow] Stripped thinking tags, remaining len={len(content)}")

        # Parse ASR correction structured output
        if self.enable_asr_correction and not self.custom_system_prompt:
            corrected_match = re.search(r'\[corrected\](.*?)\[/corrected\]', content, re.DOTALL)
            translated_match = re.search(r'\[translated\](.*?)\[/translated\]', content, re.DOTALL)
            if corrected_match and translated_match:
                self.last_corrected_source = corrected_match.group(1).strip()
                content = translated_match.group(1).strip()
                sf_logger.info(f"[SiliconFlow ASR] corrected_source={self.last_corrected_source}")
            else:
                sf_logger.warning(f"[SiliconFlow ASR] Failed to parse structured output, using raw content")

        sf_logger.debug(f"[SiliconFlow Final] content={content[:300]}")
        return content

if __name__ == "__main__":
    AUTH_KEY = "SILICONFLOW_API_KEY"
    client = SiliconFlowClient()
    client.setAuthKey(AUTH_KEY)
    models = client.getModelList()
    if models:
        print("Available models:", models)
        model = input("Select a model: ")
        client.setModel(model)
        client.updateClient()
