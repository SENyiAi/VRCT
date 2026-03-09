from os import path as os_path
from deepl import DeepLClient
try:
    from translators import translate_text as other_web_Translator
    ENABLE_TRANSLATORS = True
except Exception:
    other_web_Translator = None  # type: ignore
    ENABLE_TRANSLATORS = False

try:
    from .translation_languages import translation_lang
    from .translation_gemini import GeminiClient
    from .translation_openai import OpenAIClient
    from .translation_siliconflow import SiliconFlowClient
except Exception:
    import sys
    sys.path.append(os_path.dirname(os_path.dirname(os_path.dirname(os_path.abspath(__file__)))))
    from translation_languages import translation_lang
    from translation_gemini import GeminiClient
    from translation_openai import OpenAIClient
    from translation_siliconflow import SiliconFlowClient

from utils import errorLogging

import sys
import warnings
from typing import Any, Optional, Tuple

warnings.filterwarnings("ignore")


class Translator:
    """High-level translator facade.

    This class wraps multiple backends (DeepL, DeepL API, Google, Bing, Papago,
    and CTranslate2 local models). Optional dependencies may be unavailable at
    runtime; methods degrade gracefully and return False or an empty string on
    failure (kept compatible with existing behavior).
    """

    def __init__(self) -> None:
        self.deepl_client: Optional[DeepLClient] = None
        self.gemini_client: Optional[GeminiClient] = None
        self.openai_client: Optional[OpenAIClient] = None
        self.custom_openai_client: Optional[OpenAIClient] = None
        self.custom_openai_connected: bool = False
        self.custom_openai_client_2: Optional[OpenAIClient] = None
        self.custom_openai_connected_2: bool = False
        self.custom_openai_client_3: Optional[OpenAIClient] = None
        self.custom_openai_connected_3: bool = False
        self.siliconflow_client: Optional[SiliconFlowClient] = None
        self.is_changed_translator_parameters: bool = False
        self.is_enable_translators: bool = ENABLE_TRANSLATORS

    def authenticationDeepLAuthKey(self, auth_key: str) -> bool:
        """Authenticate DeepL API with the provided key.

        Returns True on success, False on failure.
        """
        result = True
        try:
            self.deepl_client = DeepLClient(auth_key)
            # quick smoke test
            self.deepl_client.translate_text(" ", target_lang="EN-US")
        except Exception:
            errorLogging()
            self.deepl_client = None
            result = False
        return result

    def authenticationGeminiAuthKey(self, auth_key: str, root_path: str = None) -> bool:
        """Authenticate Gemini API with the provided key.

        Returns True on success, False on failure.
        """
        self.gemini_client = GeminiClient(root_path=root_path)
        if self.gemini_client.setAuthKey(auth_key):
            return True
        else:
            self.gemini_client = None
            return False

    def getGeminiModelList(self) -> list[str]:
        """Get available Gemini models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.gemini_client is None:
            return []
        return self.gemini_client.getModelList()

    def setGeminiModel(self, model: str) -> bool:
        """Change the Gemini model used for translation.

        Returns True on success, False on failure.
        """
        if self.gemini_client is None:
            return False
        return self.gemini_client.setModel(model)

    def updateGeminiClient(self) -> None:
        """Update the Gemini client (fetch available models)."""
        self.gemini_client.updateClient()

    # ── Custom OpenAI Compatible API ──────────────────────────────
    def authenticationCustomOpenAI(self, base_url: str, api_key: str, root_path: str = None) -> bool:
        """Authenticate and connect to a custom OpenAI-compatible endpoint."""
        self.custom_openai_client = OpenAIClient(base_url=base_url, root_path=root_path, prompt_filename="translation_custom_openai.yml")
        if self.custom_openai_client.setAuthKey(api_key):
            self.custom_openai_connected = True
            return True
        else:
            self.custom_openai_client = None
            self.custom_openai_connected = False
            return False

    def getCustomOpenAIConnected(self) -> bool:
        return self.custom_openai_connected

    def setCustomOpenAIModel(self, model: str) -> bool:
        if self.custom_openai_client is None:
            return False
        # For custom endpoints, allow any model name without validation
        self.custom_openai_client.model = model
        return True

    def updateCustomOpenAIClient(self) -> None:
        if self.custom_openai_client is not None:
            self.custom_openai_client.updateClient()

    def setCustomOpenAIAsrCorrection(self, enabled: bool) -> None:
        if self.custom_openai_client is not None:
            self.custom_openai_client.enable_asr_correction = enabled

    def getCustomOpenAIAsrCorrection(self) -> bool:
        if self.custom_openai_client is not None:
            return self.custom_openai_client.enable_asr_correction
        return False

    def testCustomOpenAITranslation(self, text: str, input_lang: str, output_lang: str) -> str | bool:
        """Test translation using the Custom OpenAI client. Returns translated text or False on failure."""
        if self.custom_openai_client is None:
            return False
        return self.custom_openai_client.translate(text, input_lang=input_lang, output_lang=output_lang)

    def setCustomOpenAIMaxTokens(self, value: int) -> None:
        if self.custom_openai_client is not None:
            self.custom_openai_client.max_tokens = value

    def getCustomOpenAIMaxTokens(self) -> int:
        if self.custom_openai_client is not None:
            return self.custom_openai_client.max_tokens
        return 2048

    def setCustomOpenAITemperature(self, value: float) -> None:
        if self.custom_openai_client is not None:
            self.custom_openai_client.temperature = value

    def getCustomOpenAITemperature(self) -> float:
        if self.custom_openai_client is not None:
            return self.custom_openai_client.temperature
        return 0.3

    def setCustomOpenAICustomSystemPrompt(self, value: str) -> None:
        if self.custom_openai_client is not None:
            self.custom_openai_client.custom_system_prompt = value

    def getCustomOpenAICustomSystemPrompt(self) -> str:
        if self.custom_openai_client is not None:
            return self.custom_openai_client.custom_system_prompt
        return ""

    # ── Custom OpenAI Compatible API 2 ──────────────────────────────
    def authenticationCustomOpenAI2(self, base_url: str, api_key: str, root_path: str = None) -> bool:
        self.custom_openai_client_2 = OpenAIClient(base_url=base_url, root_path=root_path, prompt_filename="translation_custom_openai.yml")
        if self.custom_openai_client_2.setAuthKey(api_key):
            self.custom_openai_connected_2 = True
            return True
        else:
            self.custom_openai_client_2 = None
            self.custom_openai_connected_2 = False
            return False

    def getCustomOpenAI2Connected(self) -> bool:
        return self.custom_openai_connected_2

    def setCustomOpenAI2Model(self, model: str) -> bool:
        if self.custom_openai_client_2 is None:
            return False
        self.custom_openai_client_2.model = model
        return True

    def updateCustomOpenAI2Client(self) -> None:
        if self.custom_openai_client_2 is not None:
            self.custom_openai_client_2.updateClient()

    def setCustomOpenAI2AsrCorrection(self, enabled: bool) -> None:
        if self.custom_openai_client_2 is not None:
            self.custom_openai_client_2.enable_asr_correction = enabled

    def getCustomOpenAI2AsrCorrection(self) -> bool:
        if self.custom_openai_client_2 is not None:
            return self.custom_openai_client_2.enable_asr_correction
        return False

    def testCustomOpenAI2Translation(self, text: str, input_lang: str, output_lang: str) -> str | bool:
        if self.custom_openai_client_2 is None:
            return False
        return self.custom_openai_client_2.translate(text, input_lang=input_lang, output_lang=output_lang)

    def setCustomOpenAI2MaxTokens(self, value: int) -> None:
        if self.custom_openai_client_2 is not None:
            self.custom_openai_client_2.max_tokens = value

    def getCustomOpenAI2MaxTokens(self) -> int:
        if self.custom_openai_client_2 is not None:
            return self.custom_openai_client_2.max_tokens
        return 2048

    def setCustomOpenAI2Temperature(self, value: float) -> None:
        if self.custom_openai_client_2 is not None:
            self.custom_openai_client_2.temperature = value

    def getCustomOpenAI2Temperature(self) -> float:
        if self.custom_openai_client_2 is not None:
            return self.custom_openai_client_2.temperature
        return 0.3

    def setCustomOpenAI2CustomSystemPrompt(self, value: str) -> None:
        if self.custom_openai_client_2 is not None:
            self.custom_openai_client_2.custom_system_prompt = value

    def getCustomOpenAI2CustomSystemPrompt(self) -> str:
        if self.custom_openai_client_2 is not None:
            return self.custom_openai_client_2.custom_system_prompt
        return ""

    # ── Custom OpenAI Compatible API 3 ──────────────────────────────
    def authenticationCustomOpenAI3(self, base_url: str, api_key: str, root_path: str = None) -> bool:
        self.custom_openai_client_3 = OpenAIClient(base_url=base_url, root_path=root_path, prompt_filename="translation_custom_openai.yml")
        if self.custom_openai_client_3.setAuthKey(api_key):
            self.custom_openai_connected_3 = True
            return True
        else:
            self.custom_openai_client_3 = None
            self.custom_openai_connected_3 = False
            return False

    def getCustomOpenAI3Connected(self) -> bool:
        return self.custom_openai_connected_3

    def setCustomOpenAI3Model(self, model: str) -> bool:
        if self.custom_openai_client_3 is None:
            return False
        self.custom_openai_client_3.model = model
        return True

    def updateCustomOpenAI3Client(self) -> None:
        if self.custom_openai_client_3 is not None:
            self.custom_openai_client_3.updateClient()

    def setCustomOpenAI3AsrCorrection(self, enabled: bool) -> None:
        if self.custom_openai_client_3 is not None:
            self.custom_openai_client_3.enable_asr_correction = enabled

    def getCustomOpenAI3AsrCorrection(self) -> bool:
        if self.custom_openai_client_3 is not None:
            return self.custom_openai_client_3.enable_asr_correction
        return False

    def testCustomOpenAI3Translation(self, text: str, input_lang: str, output_lang: str) -> str | bool:
        if self.custom_openai_client_3 is None:
            return False
        return self.custom_openai_client_3.translate(text, input_lang=input_lang, output_lang=output_lang)

    def setCustomOpenAI3MaxTokens(self, value: int) -> None:
        if self.custom_openai_client_3 is not None:
            self.custom_openai_client_3.max_tokens = value

    def getCustomOpenAI3MaxTokens(self) -> int:
        if self.custom_openai_client_3 is not None:
            return self.custom_openai_client_3.max_tokens
        return 2048

    def setCustomOpenAI3Temperature(self, value: float) -> None:
        if self.custom_openai_client_3 is not None:
            self.custom_openai_client_3.temperature = value

    def getCustomOpenAI3Temperature(self) -> float:
        if self.custom_openai_client_3 is not None:
            return self.custom_openai_client_3.temperature
        return 0.3

    def setCustomOpenAI3CustomSystemPrompt(self, value: str) -> None:
        if self.custom_openai_client_3 is not None:
            self.custom_openai_client_3.custom_system_prompt = value

    def getCustomOpenAI3CustomSystemPrompt(self) -> str:
        if self.custom_openai_client_3 is not None:
            return self.custom_openai_client_3.custom_system_prompt
        return ""

    def authenticationOpenAIAuthKey(self, auth_key: str, base_url: str | None = None, root_path: str = None) -> bool:
        """Authenticate OpenAI (Chat Completions) API with the provided key.

        base_url を指定することで互換エンドポイント (例: Azure OpenAI 互換, Proxy) にも対応可能。
        Returns True on success, False on failure.
        """
        self.openai_client = OpenAIClient(base_url=base_url, root_path=root_path)
        if self.openai_client.setAuthKey(auth_key):
            return True
        else:
            self.openai_client = None
            return False

    def getOpenAIModelList(self) -> list[str]:
        """Get available OpenAI models.

        Returns a list of model names, or an empty list on failure.
        """
        if self.openai_client is None:
            return []
        return self.openai_client.getModelList()

    def setOpenAIModel(self, model: str) -> bool:
        """Change the OpenAI model used for translation.

        Returns True on success, False on failure.
        """
        if self.openai_client is None:
            return False
        return self.openai_client.setModel(model)

    def updateOpenAIClient(self) -> None:
        """Update the OpenAI client (fetch available models)."""
        self.openai_client.updateClient()

    def authenticationSiliconFlowAuthKey(self, auth_key: str, root_path: str = None) -> bool:
        self.siliconflow_client = SiliconFlowClient(root_path=root_path)
        if self.siliconflow_client.setAuthKey(auth_key):
            return True
        else:
            self.siliconflow_client = None
            return False

    def getSiliconFlowModelList(self) -> list[str]:
        if self.siliconflow_client is None:
            return []
        return self.siliconflow_client.getModelList()

    def setSiliconFlowModel(self, model: str) -> bool:
        if self.siliconflow_client is None:
            return False
        return self.siliconflow_client.setModel(model)

    def updateSiliconFlowClient(self) -> None:
        if self.siliconflow_client is None:
            return
        self.siliconflow_client.updateClient()

    def setSiliconFlowAsrCorrection(self, enabled: bool) -> None:
        if self.siliconflow_client is not None:
            self.siliconflow_client.enable_asr_correction = enabled

    def getSiliconFlowAsrCorrection(self) -> bool:
        if self.siliconflow_client is not None:
            return self.siliconflow_client.enable_asr_correction
        return False

    def setSiliconFlowEnableThinking(self, enabled: bool) -> None:
        if self.siliconflow_client is not None:
            self.siliconflow_client.enable_thinking = enabled

    def getSiliconFlowEnableThinking(self) -> bool:
        if self.siliconflow_client is not None:
            return self.siliconflow_client.enable_thinking
        return False

    def setSiliconFlowMaxTokens(self, value: int) -> None:
        if self.siliconflow_client is not None:
            self.siliconflow_client.max_tokens = value

    def getSiliconFlowMaxTokens(self) -> int:
        if self.siliconflow_client is not None:
            return self.siliconflow_client.max_tokens
        return 1024

    def setSiliconFlowTemperature(self, value: float) -> None:
        if self.siliconflow_client is not None:
            self.siliconflow_client.temperature = value

    def getSiliconFlowTemperature(self) -> float:
        if self.siliconflow_client is not None:
            return self.siliconflow_client.temperature
        return 0.4

    def setSiliconFlowCustomSystemPrompt(self, value: str) -> None:
        if self.siliconflow_client is not None:
            self.siliconflow_client.custom_system_prompt = value

    def getSiliconFlowCustomSystemPrompt(self) -> str:
        if self.siliconflow_client is not None:
            return self.siliconflow_client.custom_system_prompt
        return ""

    def getSiliconFlowLastCorrectedSource(self) -> str:
        if self.siliconflow_client is not None:
            return self.siliconflow_client.last_corrected_source
        return ""

    def testSiliconFlowTranslation(self, text: str, input_lang: str, output_lang: str) -> str | bool:
        """Test translation using the SiliconFlow client. Returns translated text or False on failure."""
        if self.siliconflow_client is None:
            return False
        return self.siliconflow_client.translate(text, input_lang=input_lang, output_lang=output_lang)

    def getSiliconFlowConnected(self) -> bool:
        return self.siliconflow_client is not None

    def isChangedTranslatorParameters(self) -> bool:
        return self.is_changed_translator_parameters

    def setChangedTranslatorParameters(self, is_changed: bool) -> None:
        self.is_changed_translator_parameters = is_changed


    @staticmethod
    def getLanguageCode(translator_name: str, weight_type: str, target_country: str, source_language: str, target_language: str) -> Tuple[str, str]:
        """Resolve a friendly language name to translator-specific codes.

        Returns (source_code, target_code).
        """
        match translator_name:
            case "DeepL_API":
                if target_language == "English":
                    if target_country in ["United States", "Canada", "Philippines"]:
                        target_language = "English American"
                    else:
                        target_language = "English British"
                elif target_language == "Portuguese":
                    if target_country in ["Portugal"]:
                        target_language = "Portuguese European"
                    else:
                        target_language = "Portuguese Brazilian"
                source_language = translation_lang[translator_name]["source"][source_language]
                target_language = translation_lang[translator_name]["target"][target_language]
            case _:
                source_language = translation_lang[translator_name]["source"][source_language]
                target_language = translation_lang[translator_name]["target"][target_language]
        return source_language, target_language

    def translate(self, translator_name: str, weight_type: str, source_language: str, target_language: str, target_country: str, message: str, context_history: Optional[list[dict]] = None) -> Any:
        """Translate `message` using the named translator backend.

        Args:
            translator_name: Name of the translator backend to use
            weight_type: Model weight type for CTranslate2
            source_language: Source language name
            target_language: Target language name
            target_country: Target country for locale-specific translations
            message: Text to translate
            context_history: Optional conversation context (Chat/Mic/Speaker messages)

        Returns translated string on success, or False on failure. When
        source_language == target_language the original message is returned.
        """
        try:
            if source_language == target_language:
                return message

            result: Any = ""
            source_language, target_language = self.getLanguageCode(translator_name, weight_type, target_country, source_language, target_language)
            match translator_name:
                case "DeepL":
                    if self.is_enable_translators is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="deepl",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "DeepL_API":
                    if self.is_enable_translators is True:
                        if self.deepl_client is None:
                            result = False
                        else:
                            result = self.deepl_client.translate_text(
                                message,
                                source_lang=source_language,
                                target_lang=target_language
                                ).text
                case "Gemini_API":
                    if self.gemini_client is None:
                        result = False
                    else:
                        if context_history:
                            self.gemini_client.setContextHistory(context_history)
                        result = self.gemini_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                            )
                case "OpenAI_API":
                    if self.openai_client is None:
                        result = False
                    else:
                        if context_history:
                            self.openai_client.setContextHistory(context_history)
                        result = self.openai_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Custom_OpenAI_API":
                    if self.custom_openai_client is None:
                        result = False
                    else:
                        if context_history:
                            self.custom_openai_client.setContextHistory(context_history)
                        result = self.custom_openai_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Custom_OpenAI_API_2":
                    if self.custom_openai_client_2 is None:
                        result = False
                    else:
                        if context_history:
                            self.custom_openai_client_2.setContextHistory(context_history)
                        result = self.custom_openai_client_2.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Custom_OpenAI_API_3":
                    if self.custom_openai_client_3 is None:
                        result = False
                    else:
                        if context_history:
                            self.custom_openai_client_3.setContextHistory(context_history)
                        result = self.custom_openai_client_3.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "SiliconFlow_API":
                    if self.siliconflow_client is None:
                        result = False
                    else:
                        if context_history:
                            self.siliconflow_client.setContextHistory(context_history)
                        result = self.siliconflow_client.translate(
                            message,
                            input_lang=source_language,
                            output_lang=target_language,
                        )
                case "Google":
                    if self.is_enable_translators is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="google",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "Bing":
                    if self.is_enable_translators is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="bing",
                            from_language=source_language,
                            to_language=target_language,
                        )
                case "Papago":
                    if self.is_enable_translators is True and other_web_Translator is not None:
                        result = other_web_Translator(
                            query_text=message,
                            translator="papago",
                            from_language=source_language,
                            to_language=target_language,
                        )
        except Exception:
            errorLogging()
            result = False
        return result
