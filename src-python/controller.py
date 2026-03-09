from typing import Callable, Any, List, Optional
from time import sleep
from subprocess import Popen
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
from device_manager import device_manager
from config import config
from model import model
from utils import removeLog, printLog, errorLogging, isConnectedNetwork, isValidIpAddress, isAvailableWebSocketServer
from errors import ErrorCode, VRCTError

class Controller:
    def __init__(self) -> None:
        # typed attributes to satisfy static type checkers
        self.init_mapping: dict = {}
        self.run_mapping: dict = {}
        # initialize with a no-op callable so callers can safely call self.run
        def _noop_run(status: int, endpoint: str, payload: Any = None) -> None:
            return None
        self.run: Callable[[int, str, Any], None] = _noop_run
        self.device_access_status: bool = True
        # Ensure model is initialized at controller startup so existing
        # attribute-based checks (e.g. model.overlay.initialized) continue to work.
        try:
            model.init()
        except Exception:
            # In test or headless environments initialization may fail; log and continue.
            errorLogging()

    def _is_overlay_available(self) -> bool:
        """Safe check whether overlay is present and initialized.

        This avoids AttributeError when `model` was not fully initialized.
        """
        try:
            overlay = getattr(model, "overlay", None)
            return overlay is not None and getattr(overlay, "initialized", False)
        except Exception:
            errorLogging()
            return False

    def setInitMapping(self, init_mapping:dict) -> None:
        self.init_mapping = init_mapping

    def setRunMapping(self, run_mapping:dict) -> None:
        self.run_mapping = run_mapping

    def setRun(self, run:Callable[[int, str, Any], None]) -> None:
        self.run = run
    
    def shutdown(self, *args, **kwargs) -> dict:
        """Shutdown controller and model (including telemetry).
        
        Returns:
            dict with status 200 and result True on success.
        """
        try:
            model.telemetryShutdown()
            return {"status": 200, "result": True}
        except Exception:
            errorLogging()
            return {"status": 500, "result": False}

    # response functions
    def connectedNetwork(self) -> None:
        self.run(
            200,
            self.run_mapping["connected_network"],
            True,
        )

    def disconnectedNetwork(self) -> None:
        self.run(
            200,
            self.run_mapping["connected_network"],
            False,
        )

    def enableAiModels(self) -> None:
        self.run(
            200,
            self.run_mapping["enable_ai_models"],
            True,
        )

    def disableAiModels(self) -> None:
        self.run(
            200,
            self.run_mapping["enable_ai_models"],
            False,
        )

    def updateMicHostList(self) -> None:
        self.run(
            200,
            self.run_mapping["selectable_mic_host_list"],
            model.getListMicHost(),
        )

    def updateMicDeviceList(self) -> None:
        self.run(
            200,
            self.run_mapping["selectable_mic_device_list"],
            model.getListMicDevice(),
        )

    def updateSpeakerDeviceList(self) -> None:
        self.run(
            200,
            self.run_mapping["selectable_speaker_device_list"],
            model.getListSpeakerDevice(),
        )

    def updateConfigSettings(self) -> None:
        settings = {}
        for endpoint, dict_data in self.init_mapping.items():
            response = dict_data["variable"](None)
            result = response.get("result", None)
            settings[endpoint] = result
        self.run(
            200,
            self.run_mapping["initialization_complete"],
            settings,
        )

    def restartAccessMicDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.startThreadingTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.startCheckMicEnergy(
                self.progressBarMicEnergy,
            )

    def restartAccessSpeakerDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.startThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.startCheckSpeakerEnergy(
                self.progressBarSpeakerEnergy,
            )

    def stopAccessMicDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopThreadingTranscriptionSendMessage()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            model.stopCheckMicEnergy()

    def stopAccessSpeakerDevices(self) -> None:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopThreadingTranscriptionReceiveMessage()
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            model.stopCheckSpeakerEnergy()

    def updateSelectedMicDevice(self, host, device) -> None:
        config.SELECTED_MIC_HOST = host
        config.SELECTED_MIC_DEVICE = device
        self.run(200, self.run_mapping["selected_mic_host"], config.SELECTED_MIC_HOST)
        self.run(200, self.run_mapping["selected_mic_device"], config.SELECTED_MIC_DEVICE)

    def updateSelectedSpeakerDevice(self, device) -> None:
        config.SELECTED_SPEAKER_DEVICE = device
        self.run(
            200,
            self.run_mapping["selected_speaker_device"],
            device,
        )

    def progressBarMicEnergy(self, energy) -> None:
        if energy is False:
            error_response = VRCTError.create_error_response(
                ErrorCode.DEVICE_NO_MIC,
                data=None
            )
            self.run(
                error_response["status"],
                self.run_mapping["error_device"],
                error_response["result"],
            )
        else:
            self.run(
                200,
                self.run_mapping["check_mic_volume"],
                energy,
            )

    def progressBarSpeakerEnergy(self, energy) -> None:
        if energy is False:
            error_response = VRCTError.create_error_response(
                ErrorCode.DEVICE_NO_SPEAKER,
                data=None
            )
            self.run(
                error_response["status"],
                self.run_mapping["error_device"],
                error_response["result"],
            )
        else:
            self.run(
                200,
                self.run_mapping["check_speaker_volume"],
                energy,
            )



    def micMessage(self, result: dict) -> None:
        message = result["text"]
        language = result["language"]
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No mic device detected",
                    "data": None
                },
            )

        elif isinstance(message, str) and len(message) > 0:
            model.telemetryTrackCoreFeature("mic_speech_to_text")
            translation = []
            transliteration_message = []
            transliteration_translation = []
            if model.checkKeywords(message):
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message":f"Detected by word filter: {message}"},
                )
                return
            elif model.detectRepeatSendMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                try:
                    model.telemetryTrackCoreFeature("translation")
                    translation, success = model.getInputTranslate(message, source_language=language)
                    if all(success) is not True:
                        self.run(
                            400,
                            self.run_mapping["error_translation_engine"],
                            {
                                "message":"Translation engine limit error",
                                "data": None
                            },
                        )
                    else:
                        # Replace message with ASR-corrected source text if available
                        corrected = model.getTranslatorSiliconFlowLastCorrectedSource()
                        if corrected:
                            message = corrected
                except Exception:
                    errorLogging()

            if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
                if config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                    transliteration_message = model.convertMessageToTransliteration(
                        message,
                        hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                        romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                    )

                for i, no in enumerate(config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST):
                    if (config.ENABLE_TRANSLATION is True and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["language"] == "Japanese" and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["enable"] is True
                        ):
                        transliteration_translation.append(
                            model.convertMessageToTransliteration(
                                translation[i],
                                hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                                romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                            )
                        )
                    else:
                        transliteration_translation.append([])
            else:
                transliteration_translation = [[] for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST]

            if config.ENABLE_TRANSCRIPTION_SEND is True:
                if config.SEND_MESSAGE_TO_VRC is True:
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = self.messageFormatter("SEND", [], message)
                        else:
                            osc_message = self.messageFormatter("SEND", translation, "")
                    else:
                        osc_message = self.messageFormatter("SEND", translation, message)
                    model.oscSendMessage(osc_message)

                self.run(
                    200,
                    self.run_mapping["transcription_mic"],
                    {
                        "original": {
                            "message": message,
                            "transliteration": transliteration_message
                        },
                        "translations": [
                            {
                                "message": translation_message,
                                "transliteration": transliteration
                            } for translation_message, transliteration in zip(translation, transliteration_translation)
                        ]
                    })

                if config.OVERLAY_LARGE_LOG is True and self._is_overlay_available():
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                        if len(translation) > 0:
                            overlay_image = model.createOverlayImageLargeLog(
                                "send",
                                None,
                                None,
                                translation,
                                config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                                transliteration_message,
                                transliteration_translation
                            )
                            model.updateOverlayLargeLog(overlay_image)
                    else:
                        overlay_image = model.createOverlayImageLargeLog(
                            "send",
                            message,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"],
                            translation,
                            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            transliteration_message,
                            transliteration_translation
                        )
                        model.updateOverlayLargeLog(overlay_image)

                if config.ENABLE_CLIPBOARD is True:
                    clipboard_message = self.messageFormatter("SEND", translation, message)
                    model.setCopyToClipboardAndPasteFromClipboard(clipboard_message)

                if model.checkWebSocketServerAlive() is True:
                    model.websocketSendMessage(
                        {
                            "type":"SENT",
                            "src_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            "dst_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            "message":message,
                            "translation":translation,
                            "transliteration":transliteration_translation
                        }
                    )

                if config.LOGGER_FEATURE is True:
                    translation_text = f" ({'/'.join(translation)})" if translation else ""
                    model.logger.info(f"[SENT] {message}{translation_text}")

            model.addTranslationHistory("mic", message)

    def speakerMessage(self, result:dict) -> None:
        message = result["text"]
        language = result["language"]
        if isinstance(message, bool) and message is False:
            self.run(
                400,
                self.run_mapping["error_device"],
                {
                    "message":"No speaker device detected",
                    "data": None
                },
            )
        elif isinstance(message, str) and len(message) > 0:
            model.telemetryTrackCoreFeature("speaker_speech_to_text")
            translation = []
            transliteration_message = []
            transliteration_translation = []
            if model.checkKeywords(message):
                self.run(
                    200,
                    self.run_mapping["word_filter"],
                    {"message":f"Detected by word filter: {message}"},
                )
                return
            elif model.detectRepeatReceiveMessage(message):
                return
            elif config.ENABLE_TRANSLATION is False:
                pass
            else:
                try:
                    model.telemetryTrackCoreFeature("translation")
                    translation, success = model.getOutputTranslate(message, source_language=language)
                    if all(success) is not True:
                        error_response = VRCTError.create_error_response(
                            ErrorCode.TRANSLATION_ENGINE_LIMIT,
                            data=None
                        )
                        self.run(
                            error_response["status"],
                            self.run_mapping["error_translation_engine"],
                            error_response["result"],
                        )
                    else:
                        pass
                except Exception:
                    errorLogging()

            if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
                if language == "Japanese":
                    transliteration_message = model.convertMessageToTransliteration(
                        message,
                        hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                        romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                    )

                if (config.ENABLE_TRANSLATION is True and
                    config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese"
                    ):
                    transliteration_translation.append(
                        model.convertMessageToTransliteration(
                            translation[0],
                            hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                            romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                        )
                    )
                else:
                    transliteration_translation.append([])
            else:
                transliteration_translation = [[]]

            if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
                if config.OVERLAY_SMALL_LOG is True and self._is_overlay_available():
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                        if len(translation) > 0:
                            overlay_image = model.createOverlayImageSmallLog(
                                None,
                                None,
                                translation,
                                config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                                transliteration_message,
                                transliteration_translation
                            )
                            model.updateOverlaySmallLog(overlay_image)
                    else:
                        overlay_image = model.createOverlayImageSmallLog(
                            message,
                            language,
                            translation,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            transliteration_message,
                            transliteration_translation
                        )
                        model.updateOverlaySmallLog(overlay_image)

                if config.OVERLAY_LARGE_LOG is True and self._is_overlay_available():
                    if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                        if len(translation) > 0:
                            overlay_image = model.createOverlayImageLargeLog(
                                "receive",
                                None,
                                None,
                                translation,
                                config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                                transliteration_message,
                                transliteration_translation
                            )
                            model.updateOverlayLargeLog(overlay_image)
                    else:
                        overlay_image = model.createOverlayImageLargeLog(
                            "receive",
                            message,
                            language,
                            translation,
                            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            transliteration_message,
                            transliteration_translation
                        )
                        model.updateOverlayLargeLog(overlay_image)

                if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
                    if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                        if config.ENABLE_TRANSLATION is False:
                            osc_message = self.messageFormatter("RECEIVED", [], message)
                        else:
                            osc_message = self.messageFormatter("RECEIVED", translation, "")
                    else:
                        osc_message = self.messageFormatter("RECEIVED", translation, message)
                    model.oscSendMessage(osc_message)

                # update textbox message log (Received)
                self.run(
                    200,
                    self.run_mapping["transcription_speaker"],
                    {
                        "original": {
                            "message": message,
                            "transliteration": transliteration_message
                        },
                        "translations": [
                            {
                                "message": translation_message,
                                "transliteration": transliteration
                            } for translation_message, transliteration in zip(translation, transliteration_translation)
                        ]
                    })

                if model.checkWebSocketServerAlive() is True:
                    model.websocketSendMessage(
                        {
                            "type":"RECEIVED",
                            "src_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            "dst_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                            "message":message,
                            "translation":translation,
                            "transliteration":transliteration_translation
                        }
                    )

                if config.LOGGER_FEATURE is True:
                    translation_text = f" ({'/'.join(translation)})" if translation else ""
                    model.logger.info(f"[RECEIVED] {message}{translation_text}")

            model.addTranslationHistory("speaker", message)

    def chatMessage(self, data) -> dict:
        id = data["id"]
        message = data["message"]
        if len(message) > 0:
            model.telemetryTrackCoreFeature("text_input")
            translation = []
            transliteration_message: List[Any] = []
            transliteration_translation = []
            if config.ENABLE_TRANSLATION is False:
                pass
            else:
                try:
                    model.telemetryTrackCoreFeature("translation")
                    if config.USE_EXCLUDE_WORDS is True:
                        replacement_message, replacement_dict = self.replaceExclamationsWithRandom(message)
                        translation, success = model.getInputTranslate(replacement_message)

                        message = self.removeExclamations(message)
                        for i in range(len(translation)):
                            translation[i] = self.restoreText(translation[i], replacement_dict)
                    else:
                        translation, success = model.getInputTranslate(message)

                    if all(success) is not True:
                        error_response = VRCTError.create_error_response(
                            ErrorCode.TRANSLATION_ENGINE_LIMIT,
                            data=None
                        )
                        self.run(
                            error_response["status"],
                            self.run_mapping["error_translation_engine"],
                            error_response["result"],
                        )
                    else:
                        pass
                except Exception:
                    errorLogging()

            if config.CONVERT_MESSAGE_TO_HIRAGANA is True or config.CONVERT_MESSAGE_TO_ROMAJI is True:
                if config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"] == "Japanese":
                    transliteration_message = model.convertMessageToTransliteration(
                        message,
                        hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                        romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                    )
                for i, no in enumerate(config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST):
                    if (config.ENABLE_TRANSLATION is True and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["language"] == "Japanese" and
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO][no]["enable"] is True
                        ):
                        transliteration_translation.append(
                            model.convertMessageToTransliteration(
                                translation[i],
                                hiragana=config.CONVERT_MESSAGE_TO_HIRAGANA,
                                romaji=config.CONVERT_MESSAGE_TO_ROMAJI
                            )
                        )
                    else:
                        transliteration_translation.append([])
            else:
                transliteration_translation = [[] for _ in config.SELECTED_TAB_TARGET_LANGUAGES_NO_LIST]

            # send OSC message
            if config.SEND_MESSAGE_TO_VRC is True:
                if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
                    if config.ENABLE_TRANSLATION is False:
                        osc_message = self.messageFormatter("SEND", [], message)
                    else:
                        osc_message = self.messageFormatter("SEND", translation, "")
                else:
                    osc_message = self.messageFormatter("SEND", translation, message)
                model.oscSendMessage(osc_message)

            if config.OVERLAY_LARGE_LOG is True:
                if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
                    if len(translation) > 0:
                        overlay_image = model.createOverlayImageLargeLog(
                            "send",
                            None,
                            None,
                            translation,
                            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                            transliteration_message,
                            transliteration_translation
                        )
                        model.updateOverlayLargeLog(overlay_image)
                else:
                    overlay_image = model.createOverlayImageLargeLog(
                        "send",
                        message,
                        config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO]["1"]["language"],
                        translation,
                        config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                        transliteration_message,
                        transliteration_translation
                    )
                    model.updateOverlayLargeLog(overlay_image)

            if model.checkWebSocketServerAlive() is True:
                model.websocketSendMessage(
                    {
                        "type":"CHAT",
                        "src_languages":config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
                        "dst_languages":config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
                        "message":message,
                        "translation":translation,
                        "transliteration":transliteration_translation
                    }
                )

            if config.LOGGER_FEATURE is True:
                translation_text = f" ({'/'.join(translation)})" if translation else ""
                model.logger.info(f"[CHAT] {message}{translation_text}")

        model.addTranslationHistory("chat", message)

        return {
                "status":200,
                "result":{
                    "id":id,
                    "original": {
                        "message":message,
                        "transliteration":transliteration_message
                    },
                    "translations": [
                        {
                            "message": translation_message,
                            "transliteration": transliteration
                        } for translation_message, transliteration in zip(translation, transliteration_translation)
                    ]
                }}

    @staticmethod
    def getVersion(*args, **kwargs) -> dict:
        return {"status":200, "result":config.VERSION}

    def checkSoftwareUpdated(self) -> dict:
        software_update_info = model.checkSoftwareUpdated()
        self.run(
            200,
            self.run_mapping["software_update_info"],
            software_update_info,
        )
        return {"status":200, "result": software_update_info}




    def setEnableTranslation(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSLATION is False:
            config.ENABLE_TRANSLATION = True
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setDisableTranslation(*args, **kwargs) -> dict:
        if config.ENABLE_TRANSLATION is True:
            config.ENABLE_TRANSLATION = False
        return {"status":200, "result":config.ENABLE_TRANSLATION}

    @staticmethod
    def setEnableForeground(*args, **kwargs) -> dict:
        if config.ENABLE_FOREGROUND is False:
            config.ENABLE_FOREGROUND = True
        return {"status":200, "result":config.ENABLE_FOREGROUND}

    @staticmethod
    def setDisableForeground(*args, **kwargs) -> dict:
        if config.ENABLE_FOREGROUND is True:
            config.ENABLE_FOREGROUND = False
        return {"status":200, "result":config.ENABLE_FOREGROUND}

    @staticmethod
    def getSelectedTabNo(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TAB_NO}

    def setSelectedTabNo(self, selected_tab_no:str, *args, **kwargs) -> dict:
        printLog("setSelectedTabNo", selected_tab_no)
        config.SELECTED_TAB_NO = selected_tab_no
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_TAB_NO}

    @staticmethod
    def getTranslationEngines(*args, **kwargs) -> dict:
        engines = model.findTranslationEngines(
            config.SELECTED_YOUR_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTED_TARGET_LANGUAGES[config.SELECTED_TAB_NO],
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS,
            )
        return {"status":200, "result":engines}

    @staticmethod
    def getListLanguageAndCountry(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListLanguageAndCountry()}

    @staticmethod
    def getMicHostList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListMicHost()}

    @staticmethod
    def getMicDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListMicDevice()}

    @staticmethod
    def getSpeakerDeviceList(*args, **kwargs) -> dict:
        return {"status":200, "result": model.getListSpeakerDevice()}

    @staticmethod
    def getSelectedTranslationEngines(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSLATION_ENGINES}

    @staticmethod
    def setSelectedTranslationEngines(data:dict, *args, **kwargs) -> dict:
        config.SELECTED_TRANSLATION_ENGINES = data
        return {"status":200,"result":config.SELECTED_TRANSLATION_ENGINES}

    @staticmethod
    def _enrich_languages_with_webview_code(languages: dict) -> dict:
        """Add WebView BCP-47 language codes to the selected language data."""
        from models.transcription.transcription_languages import transcription_lang
        enriched = {}
        for tab_key, tab_val in languages.items():
            enriched[tab_key] = {}
            for lang_key, lang_val in tab_val.items():
                if not isinstance(lang_val, dict):
                    enriched[tab_key][lang_key] = lang_val
                    continue
                e = dict(lang_val)
                lang = lang_val.get("language", "")
                country = lang_val.get("country", "")
                e["webview_code"] = (
                    transcription_lang
                    .get(lang, {})
                    .get(country, {})
                    .get("WebView", "en-US")
                )
                enriched[tab_key][lang_key] = e
        return enriched

    @staticmethod
    def getSelectedYourLanguages(*args, **kwargs) -> dict:
        return {"status":200, "result":Controller._enrich_languages_with_webview_code(config.SELECTED_YOUR_LANGUAGES)}

    def setSelectedYourLanguages(self, select:dict, *args, **kwargs) -> dict:
        config.SELECTED_YOUR_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":Controller._enrich_languages_with_webview_code(config.SELECTED_YOUR_LANGUAGES)}

    @staticmethod
    def getSelectedTargetLanguages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

    def setSelectedTargetLanguages(self, select:dict, *args, **kwargs) -> dict:
        config.SELECTED_TARGET_LANGUAGES = select
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.SELECTED_TARGET_LANGUAGES}

    @staticmethod
    def getTranscriptionEngines(*args, **kwargs) -> dict:
        engines = [key for key, value in config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS.items() if value is True]
        return {"status":200, "result":engines}

    @staticmethod
    def getSelectedTranscriptionEngine(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def setSelectedTranscriptionEngine(data, *args, **kwargs) -> dict:
        config.SELECTED_TRANSCRIPTION_ENGINE = str(data)
        return {"status":200, "result":config.SELECTED_TRANSCRIPTION_ENGINE}

    @staticmethod
    def getConvertMessageToRomaji(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setEnableConvertMessageToRomaji(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_ROMAJI is False:
            if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
                model.startTransliteration()
            config.CONVERT_MESSAGE_TO_ROMAJI = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def setDisableConvertMessageToRomaji(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_ROMAJI is True:
            if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
                model.stopTransliteration()
            config.CONVERT_MESSAGE_TO_ROMAJI = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_ROMAJI}

    @staticmethod
    def getConvertMessageToHiragana(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setEnableConvertMessageToHiragana(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_HIRAGANA is False:
            if config.CONVERT_MESSAGE_TO_ROMAJI is False:
                model.startTransliteration()
            config.CONVERT_MESSAGE_TO_HIRAGANA = True
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def setDisableConvertMessageToHiragana(*args, **kwargs) -> dict:
        if config.CONVERT_MESSAGE_TO_HIRAGANA is True:
            if config.CONVERT_MESSAGE_TO_ROMAJI is False:
                model.stopTransliteration()
            config.CONVERT_MESSAGE_TO_HIRAGANA = False
        return {"status":200, "result":config.CONVERT_MESSAGE_TO_HIRAGANA}

    @staticmethod
    def getMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setEnableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        if config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE is False:
            config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = True
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def setDisableMainWindowSidebarCompactMode(*args, **kwargs) -> dict:
        if config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE is True:
            config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE = False
        return {"status":200, "result":config.MAIN_WINDOW_SIDEBAR_COMPACT_MODE}

    @staticmethod
    def getTransparency(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSPARENCY}

    @staticmethod
    def setTransparency(data, *args, **kwargs) -> dict:
        config.TRANSPARENCY = int(data)
        return {"status":200, "result":config.TRANSPARENCY}

    @staticmethod
    def getUiScaling(*args, **kwargs) -> dict:
        return {"status":200, "result":config.UI_SCALING}

    @staticmethod
    def setUiScaling(data, *args, **kwargs) -> dict:
        config.UI_SCALING = int(data)
        return {"status":200, "result":config.UI_SCALING}

    @staticmethod
    def getTextboxUiScaling(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TEXTBOX_UI_SCALING}

    @staticmethod
    def setTextboxUiScaling(data, *args, **kwargs) -> dict:
        config.TEXTBOX_UI_SCALING = int(data)
        return {"status":200, "result":config.TEXTBOX_UI_SCALING}

    @staticmethod
    def getMessageBoxRatio(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MESSAGE_BOX_RATIO}

    @staticmethod
    def setMessageBoxRatio(data, *args, **kwargs) -> dict:
        config.MESSAGE_BOX_RATIO = data
        return {"status":200, "result":config.MESSAGE_BOX_RATIO}

    @staticmethod
    def getSendMessageButtonType(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def setSendMessageButtonType(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_BUTTON_TYPE = data
        return {"status":200, "result":config.SEND_MESSAGE_BUTTON_TYPE}

    @staticmethod
    def getShowResendButton(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def setEnableShowResendButton(*args, **kwargs) -> dict:
        if config.SHOW_RESEND_BUTTON is False:
            config.SHOW_RESEND_BUTTON = True
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def setDisableShowResendButton(*args, **kwargs) -> dict:
        if config.SHOW_RESEND_BUTTON is True:
            config.SHOW_RESEND_BUTTON = False
        return {"status":200, "result":config.SHOW_RESEND_BUTTON}

    @staticmethod
    def getFontFamily(*args, **kwargs) -> dict:
        return {"status":200, "result":config.FONT_FAMILY}

    @staticmethod
    def setFontFamily(data, *args, **kwargs) -> dict:
        config.FONT_FAMILY = data
        return {"status":200, "result":config.FONT_FAMILY}

    @staticmethod
    def getUiLanguage(*args, **kwargs) -> dict:
        return {"status":200, "result":config.UI_LANGUAGE}

    @staticmethod
    def setUiLanguage(data, *args, **kwargs) -> dict:
        config.UI_LANGUAGE = data
        return {"status":200, "result":config.UI_LANGUAGE}

    @staticmethod
    def getMainWindowGeometry(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def setMainWindowGeometry(data, *args, **kwargs) -> dict:
        config.MAIN_WINDOW_GEOMETRY = data
        return {"status":200, "result":config.MAIN_WINDOW_GEOMETRY}

    @staticmethod
    def getAutoMicSelect(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    def applyAutoMicSelect(self) -> None:
        device_manager.setCallbackProcessBeforeUpdateMicDevices(self.stopAccessMicDevices)
        device_manager.setCallbackDefaultMicDevice(self.updateSelectedMicDevice)
        device_manager.setCallbackProcessAfterUpdateMicDevices(self.restartAccessMicDevices)
        device_manager.forceUpdateAndSetMicDevices()
        device_manager.startMonitoring()

    def setEnableAutoMicSelect(self, *args, **kwargs) -> dict:
        if config.AUTO_MIC_SELECT is False:
            self.applyAutoMicSelect()
            config.AUTO_MIC_SELECT = True
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    @staticmethod
    def setDisableAutoMicSelect(*args, **kwargs) -> dict:
        if config.AUTO_SPEAKER_SELECT is False:
            device_manager.stopMonitoring()

        if config.AUTO_MIC_SELECT is True:
            device_manager.clearCallbackProcessBeforeUpdateMicDevices()
            device_manager.clearCallbackDefaultMicDevice()
            device_manager.clearCallbackProcessAfterUpdateMicDevices()
            config.AUTO_MIC_SELECT = False
        return {"status":200, "result":config.AUTO_MIC_SELECT}

    @staticmethod
    def getSelectedMicHost(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_MIC_HOST}

    def setSelectedMicHost(self, data, *args, **kwargs) -> dict:
        config.SELECTED_MIC_HOST = data
        config.SELECTED_MIC_DEVICE = model.getMicDefaultDevice()
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopThreadingCheckMicEnergy()
            self.startThreadingTranscriptionSendMessage()
        self.run(200, self.run_mapping["selected_mic_device"], config.SELECTED_MIC_DEVICE)
        return {"status":200, "result":config.SELECTED_MIC_HOST}

    @staticmethod
    def getSelectedMicDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_MIC_DEVICE}

    def setSelectedMicDevice(self, data, *args, **kwargs) -> dict:
        config.SELECTED_MIC_DEVICE = data
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopThreadingCheckMicEnergy()
            self.startThreadingTranscriptionSendMessage()
        return {"status":200, "result": config.SELECTED_MIC_DEVICE}

    @staticmethod
    def getMicThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_THRESHOLD}

    @staticmethod
    def setMicThreshold(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data <= config.MAX_MIC_THRESHOLD:
                config.MIC_THRESHOLD = data
                status = 200
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_THRESHOLD,
                data=config.MIC_THRESHOLD
            )
        else:
            response = {"status":status, "result":config.MIC_THRESHOLD}
        return response

    @staticmethod
    def getMicAutomaticThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setEnableMicAutomaticThreshold(*args, **kwargs) -> dict:
        if config.MIC_AUTOMATIC_THRESHOLD is False:
            config.MIC_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableMicAutomaticThreshold(*args, **kwargs) -> dict:
        if config.MIC_AUTOMATIC_THRESHOLD is True:
            config.MIC_AUTOMATIC_THRESHOLD = False
        return {"status":200, "result":config.MIC_AUTOMATIC_THRESHOLD}

    @staticmethod
    def getMicRecordTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_RECORD_TIMEOUT}

    @staticmethod
    def setMicRecordTimeout(data, *args, **kwargs) -> dict:
        printLog("Set Mic Record Timeout", data)
        try:
            data = int(data)
            if 0 <= data <= config.MIC_PHRASE_TIMEOUT:
                config.MIC_RECORD_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT,
                data=config.MIC_RECORD_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.MIC_RECORD_TIMEOUT}
        return response

    @staticmethod
    def getMicPhraseTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_PHRASE_TIMEOUT}

    @staticmethod
    def setMicPhraseTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if data >= config.MIC_RECORD_TIMEOUT:
                config.MIC_PHRASE_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT,
                data=config.MIC_PHRASE_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.MIC_PHRASE_TIMEOUT}
        return response

    @staticmethod
    def getMicMaxPhrases(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_MAX_PHRASES}

    @staticmethod
    def setMicMaxPhrases(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data:
                config.MIC_MAX_PHRASES = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_MIC_MAX_PHRASES,
                data=config.MIC_MAX_PHRASES
            )
        else:
            response = {"status":200, "result":config.MIC_MAX_PHRASES}
        return response

    @staticmethod
    def getMicWordFilter(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_WORD_FILTER}

    @staticmethod
    def setMicWordFilter(data, *args, **kwargs) -> dict:
        config.MIC_WORD_FILTER = sorted(set(data), key=data.index)
        model.resetKeywordProcessor()
        model.addKeywords()
        return {"status":200, "result":config.MIC_WORD_FILTER}

    @staticmethod
    def getMicAvgLogprob(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_AVG_LOGPROB}

    @staticmethod
    def setMicAvgLogprob(data, *args, **kwargs) -> dict:
        config.MIC_AVG_LOGPROB = float(data)
        return {"status":200, "result":config.MIC_AVG_LOGPROB}

    @staticmethod
    def getMicNoSpeechProb(*args, **kwargs) -> dict:
        return {"status":200, "result":config.MIC_NO_SPEECH_PROB}

    @staticmethod
    def setMicNoSpeechProb(data, *args, **kwargs) -> dict:
        config.MIC_NO_SPEECH_PROB = float(data)
        return {"status":200, "result":config.MIC_NO_SPEECH_PROB}

    @staticmethod
    def getAutoSpeakerSelect(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    def applyAutoSpeakerSelect(self) -> None:
        device_manager.setCallbackProcessBeforeUpdateSpeakerDevices(self.stopAccessSpeakerDevices)
        device_manager.setCallbackDefaultSpeakerDevice(self.updateSelectedSpeakerDevice)
        device_manager.setCallbackProcessAfterUpdateSpeakerDevices(self.restartAccessSpeakerDevices)
        device_manager.forceUpdateAndSetSpeakerDevices()
        device_manager.startMonitoring()

    def setEnableAutoSpeakerSelect(self, *args, **kwargs) -> dict:
        if config.AUTO_SPEAKER_SELECT is False:
            self.applyAutoSpeakerSelect()
            config.AUTO_SPEAKER_SELECT = True
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def setDisableAutoSpeakerSelect(*args, **kwargs) -> dict:
        if config.AUTO_MIC_SELECT is False:
            device_manager.stopMonitoring()

        if config.AUTO_SPEAKER_SELECT is True:
            device_manager.clearCallbackProcessBeforeUpdateSpeakerDevices()
            device_manager.clearCallbackDefaultSpeakerDevice()
            device_manager.clearCallbackProcessAfterUpdateSpeakerDevices()
            config.AUTO_SPEAKER_SELECT = False
        return {"status":200, "result":config.AUTO_SPEAKER_SELECT}

    @staticmethod
    def getSelectedSpeakerDevice(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

    def setSelectedSpeakerDevice(self, data, *args, **kwargs) -> dict:
        config.SELECTED_SPEAKER_DEVICE = data
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.stopThreadingCheckSpeakerEnergy()
            self.startThreadingTranscriptionReceiveMessage()
        return {"status":200, "result":config.SELECTED_SPEAKER_DEVICE}

    @staticmethod
    def getSpeakerThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_THRESHOLD}

    @staticmethod
    def setSpeakerThreshold(data, *args, **kwargs) -> dict:
        printLog("Set Speaker Energy Threshold", data)
        try:
            data = int(data)
            if 0 <= data <= config.MAX_SPEAKER_THRESHOLD:
                config.SPEAKER_THRESHOLD = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_THRESHOLD,
                data=config.SPEAKER_THRESHOLD
            )
        else:
            response = {"status":200, "result":config.SPEAKER_THRESHOLD}
        return response

    @staticmethod
    def getSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setEnableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        if config.SPEAKER_AUTOMATIC_THRESHOLD is False:
            config.SPEAKER_AUTOMATIC_THRESHOLD = True
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def setDisableSpeakerAutomaticThreshold(*args, **kwargs) -> dict:
        if config.SPEAKER_AUTOMATIC_THRESHOLD is True:
            config.SPEAKER_AUTOMATIC_THRESHOLD = False
        return {"status":200, "result":config.SPEAKER_AUTOMATIC_THRESHOLD}

    @staticmethod
    def getSpeakerRecordTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_RECORD_TIMEOUT}

    @staticmethod
    def setSpeakerRecordTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data <= config.SPEAKER_PHRASE_TIMEOUT:
                config.SPEAKER_RECORD_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT,
                data=config.SPEAKER_RECORD_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.SPEAKER_RECORD_TIMEOUT}
        return response

    @staticmethod
    def getSpeakerPhraseTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_PHRASE_TIMEOUT}

    @staticmethod
    def setSpeakerPhraseTimeout(data, *args, **kwargs) -> dict:
        try:
            data = int(data)
            if 0 <= data and data >= config.SPEAKER_RECORD_TIMEOUT:
                config.SPEAKER_PHRASE_TIMEOUT = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT,
                data=config.SPEAKER_PHRASE_TIMEOUT
            )
        else:
            response = {"status":200, "result":config.SPEAKER_PHRASE_TIMEOUT}
        return response

    @staticmethod
    def getSpeakerMaxPhrases(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_MAX_PHRASES}

    @staticmethod
    def setSpeakerMaxPhrases(data, *args, **kwargs) -> dict:
        printLog("Set Speaker Max Phrases", data)
        try:
            data = int(data)
            if 0 <= data:
                config.SPEAKER_MAX_PHRASES = data
            else:
                raise ValueError()
        except Exception:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES,
                data=config.SPEAKER_MAX_PHRASES
            )
        else:
            response = {"status":200, "result":config.SPEAKER_MAX_PHRASES}
        return response

    @staticmethod
    def getHotkeys(*args, **kwargs) -> dict:
        return {"status":200, "result":config.HOTKEYS}

    @staticmethod
    def setHotkeys(data, *args, **kwargs) -> dict:
        config.HOTKEYS = data
        return {"status":200, "result":config.HOTKEYS}

    @staticmethod
    def getPluginsStatus(*args, **kwargs) -> dict:
        return {"status":200, "result":config.PLUGINS_STATUS}

    @staticmethod
    def setPluginsStatus(data, *args, **kwargs) -> dict:
        config.PLUGINS_STATUS = data
        return {"status":200, "result":config.PLUGINS_STATUS}

    @staticmethod
    def getSpeakerAvgLogprob(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}

    @staticmethod
    def setSpeakerAvgLogprob(data, *args, **kwargs) -> dict:
        config.SPEAKER_AVG_LOGPROB = float(data)
        return {"status":200, "result":config.SPEAKER_AVG_LOGPROB}

    @staticmethod
    def getSpeakerNoSpeechProb(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}

    @staticmethod
    def setSpeakerNoSpeechProb(data, *args, **kwargs) -> dict:
        config.SPEAKER_NO_SPEECH_PROB = float(data)
        return {"status":200, "result":config.SPEAKER_NO_SPEECH_PROB}

    @staticmethod
    def getOscIpAddress(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OSC_IP_ADDRESS}

    def setOscIpAddress(self, data, *args, **kwargs) -> dict:
        if isValidIpAddress(data) is False:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_INVALID_IP,
                data=config.OSC_IP_ADDRESS
            )
        else:
            try:
                model.setOscIpAddress(data)
                config.OSC_IP_ADDRESS = data
                if model.getIsOscQueryEnabled() is True:
                    self.enableOscQuery()
                else:
                    mute_sync_info_flag = False
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self.setDisableVrcMicMuteSync()
                        mute_sync_info_flag = True
                    self.disableOscQuery(mute_sync_info=mute_sync_info_flag)

                response = {"status":200, "result":config.OSC_IP_ADDRESS}
            except Exception:
                model.setOscIpAddress(config.OSC_IP_ADDRESS)
                response = VRCTError.create_error_response(
                    ErrorCode.VALIDATION_CANNOT_SET_IP,
                    data=config.OSC_IP_ADDRESS
                )
        return response

    @staticmethod
    def getOscPort(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OSC_PORT}

    @staticmethod
    def setOscPort(data, *args, **kwargs) -> dict:
        config.OSC_PORT = int(data)
        model.setOscPort(config.OSC_PORT)
        return {"status":200, "result":config.OSC_PORT}

    @staticmethod
    def getNotificationVrcSfx(*args, **kwargs) -> dict:
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setEnableNotificationVrcSfx(*args, **kwargs) -> dict:
        if config.NOTIFICATION_VRC_SFX is False:
            config.NOTIFICATION_VRC_SFX = True
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def setDisableNotificationVrcSfx(*args, **kwargs) -> dict:
        if config.NOTIFICATION_VRC_SFX is True:
            config.NOTIFICATION_VRC_SFX = False
        return {"status":200, "result":config.NOTIFICATION_VRC_SFX}

    @staticmethod
    def getDeepLAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["DeepL_API"]}

    def setDeeplAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set DeepL Auth Key", data)
        translator_name = "DeepL_API"
        try:
            data = str(data)
            if len(data) == 36 or len(data) == 39:
                result = model.authenticationTranslatorDeepLAuthKey(auth_key=data)
                if result is True:
                    key = data
                    auth_keys = config.AUTH_KEYS
                    auth_keys[translator_name] = key
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_DEEPL_FAILED,
                        data=config.AUTH_KEYS[translator_name]
                    )
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.AUTH_DEEPL_LENGTH,
                    data=config.AUTH_KEYS[translator_name]
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.AUTH_KEYS[translator_name]
            )
        return response

    def delDeeplAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "DeepL_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}







    def getGeminiAuthKey(self, *args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["Gemini_API"]}

    def setGeminiAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set Gemini Auth Key", data)
        translator_name = "Gemini_API"
        try:
            data = str(data)
            if len(data) >= 39:
                result = model.authenticationTranslatorGeminiAuthKey(auth_key=data)
                if result is True:
                    key = data
                    auth_keys = config.AUTH_KEYS
                    auth_keys[translator_name] = key
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    config.SELECTABLE_GEMINI_MODEL_LIST = model.getTranslatorGeminiModelList()
                    self.run(200, self.run_mapping["selectable_gemini_model_list"], config.SELECTABLE_GEMINI_MODEL_LIST)
                    if config.SELECTED_GEMINI_MODEL not in config.SELECTABLE_GEMINI_MODEL_LIST:
                        config.SELECTED_GEMINI_MODEL = config.SELECTABLE_GEMINI_MODEL_LIST[0]
                    model.setTranslatorGeminiModel(model=config.SELECTED_GEMINI_MODEL)
                    self.run(200, self.run_mapping["selected_gemini_model"], config.SELECTED_GEMINI_MODEL)
                    model.updateTranslatorGeminiClient()
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_GEMINI_FAILED,
                        data=None
                    )
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.AUTH_GEMINI_LENGTH,
                    data=None
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delGeminiAuthKey()
        return response

    def delGeminiAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "Gemini_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_GEMINI_MODEL_LIST = []
        config.SELECTED_GEMINI_MODEL = None
        self.run(200, self.run_mapping["selectable_gemini_model_list"], config.SELECTABLE_GEMINI_MODEL_LIST)
        self.run(200, self.run_mapping["selected_gemini_model"], config.SELECTED_GEMINI_MODEL)
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    def getGeminiModelList(self, *args, **kwargs) -> dict:
        return {"status":200, "result": config.SELECTABLE_GEMINI_MODEL_LIST}

    def getGeminiModel(self, *args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_GEMINI_MODEL}

    def setGeminiModel(self, data, *args, **kwargs) -> dict:
        printLog("Set Gemini Model", data)
        try:
            data = str(data)
            result = model.setTranslatorGeminiModel(model=data)
            if result is True:
                config.SELECTED_GEMINI_MODEL = data
                model.setTranslatorGeminiModel(model=config.SELECTED_GEMINI_MODEL)
                model.updateTranslatorGeminiClient()
                response = {"status":200, "result":config.SELECTED_GEMINI_MODEL}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.MODEL_GEMINI_INVALID,
                    data=config.SELECTED_GEMINI_MODEL
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.SELECTED_GEMINI_MODEL
            )
        return response

    @staticmethod
    def getOpenAIAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["OpenAI_API"]}

    def setOpenAIAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set OpenAI Auth Key", data)
        translator_name = "OpenAI_API"
        try:
            data = str(data)
            if data.startswith("sk-") and len(data) >= 164:
                result = model.authenticationTranslatorOpenAIAuthKey(auth_key=data)
                if result is True:
                    key = data
                    auth_keys = config.AUTH_KEYS
                    auth_keys[translator_name] = key
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    config.SELECTABLE_OPENAI_MODEL_LIST = model.getTranslatorOpenAIModelList()
                    self.run(200, self.run_mapping["selectable_openai_model_list"], config.SELECTABLE_OPENAI_MODEL_LIST)
                    if config.SELECTED_OPENAI_MODEL not in config.SELECTABLE_OPENAI_MODEL_LIST:
                        config.SELECTED_OPENAI_MODEL = config.SELECTABLE_OPENAI_MODEL_LIST[0]
                    model.setTranslatorOpenAIModel(model=config.SELECTED_OPENAI_MODEL)
                    self.run(200, self.run_mapping["selected_openai_model"], config.SELECTED_OPENAI_MODEL)
                    model.updateTranslatorOpenAIClient()
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_OPENAI_FAILED,
                        data=None
                    )
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.AUTH_OPENAI_INVALID,
                    data=None
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delOpenAIAuthKey()
        return response

    def delOpenAIAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "OpenAI_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_OPENAI_MODEL_LIST = []
        config.SELECTED_OPENAI_MODEL = None
        self.run(200, self.run_mapping["selectable_openai_model_list"], config.SELECTABLE_OPENAI_MODEL_LIST)
        self.run(200, self.run_mapping["selected_openai_model"], config.SELECTED_OPENAI_MODEL)
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    def getOpenAIModelList(self, *args, **kwargs) -> dict:
        return {"status":200, "result": config.SELECTABLE_OPENAI_MODEL_LIST}

    def getOpenAIModel(self, *args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_OPENAI_MODEL}

    def setOpenAIModel(self, data, *args, **kwargs) -> dict:
        printLog("Set OpenAI Model", data)
        try:
            data = str(data)
            result = model.setTranslatorOpenAIModel(model=data)
            if result is True:
                config.SELECTED_OPENAI_MODEL = data
                model.setTranslatorOpenAIModel(model=config.SELECTED_OPENAI_MODEL)
                model.updateTranslatorOpenAIClient()
                response = {"status":200, "result":config.SELECTED_OPENAI_MODEL}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.MODEL_OPENAI_INVALID,
                    data=config.SELECTED_OPENAI_MODEL
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.SELECTED_OPENAI_MODEL
            )
        return response

    # --- Custom OpenAI Compatible API ---
    @staticmethod
    def getCustomOpenAIURL(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_URL}

    def setCustomOpenAIURL(self, data, *args, **kwargs) -> dict:
        printLog("Set Custom OpenAI URL", data)
        try:
            data = str(data)
            config.CUSTOM_OPENAI_URL = data
            response = {"status":200, "result":config.CUSTOM_OPENAI_URL}
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_URL)
        return response

    @staticmethod
    def getCustomOpenAIAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["Custom_OpenAI_API"]}

    def setCustomOpenAIAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set Custom OpenAI Auth Key", data)
        try:
            data = str(data)
            auth_keys = config.AUTH_KEYS
            auth_keys["Custom_OpenAI_API"] = data
            config.AUTH_KEYS = auth_keys
            response = {"status":200, "result":config.AUTH_KEYS["Custom_OpenAI_API"]}
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(e, data=None)
        return response

    def delCustomOpenAIAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "Custom_OpenAI_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.run(200, self.run_mapping["custom_openai_connection"], False)
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    @staticmethod
    def getCustomOpenAIModel(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_MODEL}

    def setCustomOpenAIModel(self, data, *args, **kwargs) -> dict:
        printLog("Set Custom OpenAI Model", data)
        try:
            data = str(data)
            config.CUSTOM_OPENAI_MODEL = data
            response = {"status":200, "result":config.CUSTOM_OPENAI_MODEL}
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_MODEL)
        return response

    def getCustomOpenAIConnection(self, *args, **kwargs) -> dict:
        return {"status":200, "result":model.getTranslatorCustomOpenAIConnected()}

    def checkCustomOpenAIConnection(self, *args, **kwargs) -> dict:
        printLog("Check Custom OpenAI Connection")
        translator_name = "Custom_OpenAI_API"
        try:
            base_url = config.CUSTOM_OPENAI_URL
            api_key = config.AUTH_KEYS.get(translator_name)
            model_name = config.CUSTOM_OPENAI_MODEL

            if not base_url or not api_key:
                raise Exception("Custom OpenAI URL or API Key is not set")

            result = model.authenticationTranslatorCustomOpenAI(base_url=base_url, api_key=api_key)
            if result is True:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                if model_name:
                    model.setTranslatorCustomOpenAIModel(model=model_name)
                    model.updateTranslatorCustomOpenAIClient()
                model.setTranslatorCustomOpenAIAsrCorrection(config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION)
                model.setTranslatorCustomOpenAIMaxTokens(config.CUSTOM_OPENAI_MAX_TOKENS)
                model.setTranslatorCustomOpenAITemperature(config.CUSTOM_OPENAI_TEMPERATURE)
                model.setTranslatorCustomOpenAICustomSystemPrompt(config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT)
                self.updateTranslationEngineAndEngineList()
                response = {"status":200, "result":True}
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
                self.updateTranslationEngineAndEngineList()
                response = VRCTError.create_error_response(
                    ErrorCode.CONNECTION_CUSTOM_OPENAI_FAILED,
                    data=False
                )
        except Exception as e:
            errorLogging()
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
            self.updateTranslationEngineAndEngineList()
            response = VRCTError.create_exception_error_response(
                e,
                data=False
            )
        return response

    @staticmethod
    def getCustomOpenAIAsrCorrection(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION}

    def setEnableCustomOpenAIAsrCorrection(self, *args, **kwargs) -> dict:
        config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION = True
        model.setTranslatorCustomOpenAIAsrCorrection(True)
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION}

    def setDisableCustomOpenAIAsrCorrection(self, *args, **kwargs) -> dict:
        config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION = False
        model.setTranslatorCustomOpenAIAsrCorrection(False)
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION}

    def testCustomOpenAITranslation(self, data, *args, **kwargs) -> dict:
        printLog("Test Custom OpenAI Translation", data)
        try:
            text = str(data.get("text", ""))
            input_lang = str(data.get("input_lang", ""))
            output_lang = str(data.get("output_lang", ""))
            if not text or not input_lang or not output_lang:
                raise Exception("Missing required fields: text, input_lang, output_lang")
            result = model.testTranslatorCustomOpenAITranslation(text, input_lang, output_lang)
            if result is False:
                raise Exception("Custom OpenAI client is not connected")
            response = {"status":200, "result":result}
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(e, data=None)
        return response

    # Extra params for Custom OpenAI slot 1
    @staticmethod
    def getCustomOpenAIMaxTokens(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_MAX_TOKENS}

    def setCustomOpenAIMaxTokens(self, data, *args, **kwargs) -> dict:
        try:
            config.CUSTOM_OPENAI_MAX_TOKENS = int(data)
            model.setTranslatorCustomOpenAIMaxTokens(int(data))
            if model.getTranslatorCustomOpenAIConnected():
                model.updateTranslatorCustomOpenAIClient()
            return {"status":200, "result":config.CUSTOM_OPENAI_MAX_TOKENS}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_MAX_TOKENS)

    @staticmethod
    def getCustomOpenAITemperature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_TEMPERATURE}

    def setCustomOpenAITemperature(self, data, *args, **kwargs) -> dict:
        try:
            config.CUSTOM_OPENAI_TEMPERATURE = float(data)
            model.setTranslatorCustomOpenAITemperature(float(data))
            if model.getTranslatorCustomOpenAIConnected():
                model.updateTranslatorCustomOpenAIClient()
            return {"status":200, "result":config.CUSTOM_OPENAI_TEMPERATURE}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_TEMPERATURE)

    @staticmethod
    def getCustomOpenAICustomSystemPrompt(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT}

    def setCustomOpenAICustomSystemPrompt(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT = data
            model.setTranslatorCustomOpenAICustomSystemPrompt(data)
            return {"status":200, "result":config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT)

    # --- Custom OpenAI Compatible API 2 ---
    @staticmethod
    def getCustomOpenAI2URL(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_URL_2}

    def setCustomOpenAI2URL(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_URL_2 = data
            return {"status":200, "result":config.CUSTOM_OPENAI_URL_2}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_URL_2)

    @staticmethod
    def getCustomOpenAI2AuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["Custom_OpenAI_API_2"]}

    def setCustomOpenAI2AuthKey(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            auth_keys = config.AUTH_KEYS
            auth_keys["Custom_OpenAI_API_2"] = data
            config.AUTH_KEYS = auth_keys
            return {"status":200, "result":config.AUTH_KEYS["Custom_OpenAI_API_2"]}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=None)

    def delCustomOpenAI2AuthKey(self, *args, **kwargs) -> dict:
        translator_name = "Custom_OpenAI_API_2"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.run(200, self.run_mapping["custom_openai_2_connection"], False)
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    @staticmethod
    def getCustomOpenAI2Model(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_MODEL_2}

    def setCustomOpenAI2Model(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_MODEL_2 = data
            return {"status":200, "result":config.CUSTOM_OPENAI_MODEL_2}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_MODEL_2)

    def getCustomOpenAI2Connection(self, *args, **kwargs) -> dict:
        return {"status":200, "result":model.getTranslatorCustomOpenAI2Connected()}

    def checkCustomOpenAI2Connection(self, *args, **kwargs) -> dict:
        translator_name = "Custom_OpenAI_API_2"
        try:
            base_url = config.CUSTOM_OPENAI_URL_2
            api_key = config.AUTH_KEYS.get(translator_name)
            model_name = config.CUSTOM_OPENAI_MODEL_2
            if not base_url or not api_key:
                raise Exception("Custom OpenAI 2 URL or API Key is not set")
            result = model.authenticationTranslatorCustomOpenAI2(base_url=base_url, api_key=api_key)
            if result is True:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                if model_name:
                    model.setTranslatorCustomOpenAI2Model(model=model_name)
                    model.updateTranslatorCustomOpenAI2Client()
                model.setTranslatorCustomOpenAI2AsrCorrection(config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_2)
                model.setTranslatorCustomOpenAI2MaxTokens(config.CUSTOM_OPENAI_MAX_TOKENS_2)
                model.setTranslatorCustomOpenAI2Temperature(config.CUSTOM_OPENAI_TEMPERATURE_2)
                model.setTranslatorCustomOpenAI2CustomSystemPrompt(config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_2)
                self.updateTranslationEngineAndEngineList()
                response = {"status":200, "result":True}
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
                self.updateTranslationEngineAndEngineList()
                response = VRCTError.create_error_response(ErrorCode.CONNECTION_CUSTOM_OPENAI_2_FAILED, data=False)
        except Exception as e:
            errorLogging()
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
            self.updateTranslationEngineAndEngineList()
            response = VRCTError.create_exception_error_response(e, data=False)
        return response

    @staticmethod
    def getCustomOpenAI2AsrCorrection(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_2}

    def setEnableCustomOpenAI2AsrCorrection(self, *args, **kwargs) -> dict:
        config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_2 = True
        model.setTranslatorCustomOpenAI2AsrCorrection(True)
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_2}

    def setDisableCustomOpenAI2AsrCorrection(self, *args, **kwargs) -> dict:
        config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_2 = False
        model.setTranslatorCustomOpenAI2AsrCorrection(False)
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_2}

    def testCustomOpenAI2Translation(self, data, *args, **kwargs) -> dict:
        try:
            text = str(data.get("text", ""))
            input_lang = str(data.get("input_lang", ""))
            output_lang = str(data.get("output_lang", ""))
            if not text or not input_lang or not output_lang:
                raise Exception("Missing required fields")
            result = model.testTranslatorCustomOpenAI2Translation(text, input_lang, output_lang)
            if result is False:
                raise Exception("Custom OpenAI 2 client is not connected")
            return {"status":200, "result":result}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=None)

    @staticmethod
    def getCustomOpenAI2MaxTokens(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_MAX_TOKENS_2}

    def setCustomOpenAI2MaxTokens(self, data, *args, **kwargs) -> dict:
        try:
            config.CUSTOM_OPENAI_MAX_TOKENS_2 = int(data)
            model.setTranslatorCustomOpenAI2MaxTokens(int(data))
            if model.getTranslatorCustomOpenAI2Connected():
                model.updateTranslatorCustomOpenAI2Client()
            return {"status":200, "result":config.CUSTOM_OPENAI_MAX_TOKENS_2}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_MAX_TOKENS_2)

    @staticmethod
    def getCustomOpenAI2Temperature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_TEMPERATURE_2}

    def setCustomOpenAI2Temperature(self, data, *args, **kwargs) -> dict:
        try:
            config.CUSTOM_OPENAI_TEMPERATURE_2 = float(data)
            model.setTranslatorCustomOpenAI2Temperature(float(data))
            if model.getTranslatorCustomOpenAI2Connected():
                model.updateTranslatorCustomOpenAI2Client()
            return {"status":200, "result":config.CUSTOM_OPENAI_TEMPERATURE_2}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_TEMPERATURE_2)

    @staticmethod
    def getCustomOpenAI2CustomSystemPrompt(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_2}

    def setCustomOpenAI2CustomSystemPrompt(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_2 = data
            model.setTranslatorCustomOpenAI2CustomSystemPrompt(data)
            return {"status":200, "result":config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_2}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_2)

    # --- Custom OpenAI Compatible API 3 ---
    @staticmethod
    def getCustomOpenAI3URL(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_URL_3}

    def setCustomOpenAI3URL(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_URL_3 = data
            return {"status":200, "result":config.CUSTOM_OPENAI_URL_3}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_URL_3)

    @staticmethod
    def getCustomOpenAI3AuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["Custom_OpenAI_API_3"]}

    def setCustomOpenAI3AuthKey(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            auth_keys = config.AUTH_KEYS
            auth_keys["Custom_OpenAI_API_3"] = data
            config.AUTH_KEYS = auth_keys
            return {"status":200, "result":config.AUTH_KEYS["Custom_OpenAI_API_3"]}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=None)

    def delCustomOpenAI3AuthKey(self, *args, **kwargs) -> dict:
        translator_name = "Custom_OpenAI_API_3"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.run(200, self.run_mapping["custom_openai_3_connection"], False)
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    @staticmethod
    def getCustomOpenAI3Model(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_MODEL_3}

    def setCustomOpenAI3Model(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_MODEL_3 = data
            return {"status":200, "result":config.CUSTOM_OPENAI_MODEL_3}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_MODEL_3)

    def getCustomOpenAI3Connection(self, *args, **kwargs) -> dict:
        return {"status":200, "result":model.getTranslatorCustomOpenAI3Connected()}

    def checkCustomOpenAI3Connection(self, *args, **kwargs) -> dict:
        translator_name = "Custom_OpenAI_API_3"
        try:
            base_url = config.CUSTOM_OPENAI_URL_3
            api_key = config.AUTH_KEYS.get(translator_name)
            model_name = config.CUSTOM_OPENAI_MODEL_3
            if not base_url or not api_key:
                raise Exception("Custom OpenAI 3 URL or API Key is not set")
            result = model.authenticationTranslatorCustomOpenAI3(base_url=base_url, api_key=api_key)
            if result is True:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                if model_name:
                    model.setTranslatorCustomOpenAI3Model(model=model_name)
                    model.updateTranslatorCustomOpenAI3Client()
                model.setTranslatorCustomOpenAI3AsrCorrection(config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_3)
                model.setTranslatorCustomOpenAI3MaxTokens(config.CUSTOM_OPENAI_MAX_TOKENS_3)
                model.setTranslatorCustomOpenAI3Temperature(config.CUSTOM_OPENAI_TEMPERATURE_3)
                model.setTranslatorCustomOpenAI3CustomSystemPrompt(config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_3)
                self.updateTranslationEngineAndEngineList()
                response = {"status":200, "result":True}
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
                self.updateTranslationEngineAndEngineList()
                response = VRCTError.create_error_response(ErrorCode.CONNECTION_CUSTOM_OPENAI_3_FAILED, data=False)
        except Exception as e:
            errorLogging()
            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
            self.updateTranslationEngineAndEngineList()
            response = VRCTError.create_exception_error_response(e, data=False)
        return response

    @staticmethod
    def getCustomOpenAI3AsrCorrection(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_3}

    def setEnableCustomOpenAI3AsrCorrection(self, *args, **kwargs) -> dict:
        config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_3 = True
        model.setTranslatorCustomOpenAI3AsrCorrection(True)
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_3}

    def setDisableCustomOpenAI3AsrCorrection(self, *args, **kwargs) -> dict:
        config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_3 = False
        model.setTranslatorCustomOpenAI3AsrCorrection(False)
        return {"status":200, "result":config.CUSTOM_OPENAI_ENABLE_ASR_CORRECTION_3}

    def testCustomOpenAI3Translation(self, data, *args, **kwargs) -> dict:
        try:
            text = str(data.get("text", ""))
            input_lang = str(data.get("input_lang", ""))
            output_lang = str(data.get("output_lang", ""))
            if not text or not input_lang or not output_lang:
                raise Exception("Missing required fields")
            result = model.testTranslatorCustomOpenAI3Translation(text, input_lang, output_lang)
            if result is False:
                raise Exception("Custom OpenAI 3 client is not connected")
            return {"status":200, "result":result}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=None)

    @staticmethod
    def getCustomOpenAI3MaxTokens(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_MAX_TOKENS_3}

    def setCustomOpenAI3MaxTokens(self, data, *args, **kwargs) -> dict:
        try:
            config.CUSTOM_OPENAI_MAX_TOKENS_3 = int(data)
            model.setTranslatorCustomOpenAI3MaxTokens(int(data))
            if model.getTranslatorCustomOpenAI3Connected():
                model.updateTranslatorCustomOpenAI3Client()
            return {"status":200, "result":config.CUSTOM_OPENAI_MAX_TOKENS_3}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_MAX_TOKENS_3)

    @staticmethod
    def getCustomOpenAI3Temperature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_TEMPERATURE_3}

    def setCustomOpenAI3Temperature(self, data, *args, **kwargs) -> dict:
        try:
            config.CUSTOM_OPENAI_TEMPERATURE_3 = float(data)
            model.setTranslatorCustomOpenAI3Temperature(float(data))
            if model.getTranslatorCustomOpenAI3Connected():
                model.updateTranslatorCustomOpenAI3Client()
            return {"status":200, "result":config.CUSTOM_OPENAI_TEMPERATURE_3}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_TEMPERATURE_3)

    @staticmethod
    def getCustomOpenAI3CustomSystemPrompt(*args, **kwargs) -> dict:
        return {"status":200, "result":config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_3}

    def setCustomOpenAI3CustomSystemPrompt(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_3 = data
            model.setTranslatorCustomOpenAI3CustomSystemPrompt(data)
            return {"status":200, "result":config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_3}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.CUSTOM_OPENAI_CUSTOM_SYSTEM_PROMPT_3)

    # --- Fallback Settings ---
    @staticmethod
    def getTranslationFallbackEnabled(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSLATION_FALLBACK_ENABLED}

    def setEnableTranslationFallback(self, *args, **kwargs) -> dict:
        config.TRANSLATION_FALLBACK_ENABLED = True
        return {"status":200, "result":config.TRANSLATION_FALLBACK_ENABLED}

    def setDisableTranslationFallback(self, *args, **kwargs) -> dict:
        config.TRANSLATION_FALLBACK_ENABLED = False
        return {"status":200, "result":config.TRANSLATION_FALLBACK_ENABLED}

    @staticmethod
    def getTranslationFallbackTimeout(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSLATION_FALLBACK_TIMEOUT}

    def setTranslationFallbackTimeout(self, data, *args, **kwargs) -> dict:
        try:
            config.TRANSLATION_FALLBACK_TIMEOUT = float(data)
            return {"status":200, "result":config.TRANSLATION_FALLBACK_TIMEOUT}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.TRANSLATION_FALLBACK_TIMEOUT)

    @staticmethod
    def getTranslationFallbackEngine(*args, **kwargs) -> dict:
        return {"status":200, "result":config.TRANSLATION_FALLBACK_ENGINE}

    def setTranslationFallbackEngine(self, data, *args, **kwargs) -> dict:
        try:
            config.TRANSLATION_FALLBACK_ENGINE = str(data)
            return {"status":200, "result":config.TRANSLATION_FALLBACK_ENGINE}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.TRANSLATION_FALLBACK_ENGINE)











    def getSiliconFlowAuthKey(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTH_KEYS["SiliconFlow_API"]}

    def setSiliconFlowAuthKey(self, data, *args, **kwargs) -> dict:
        printLog("Set SiliconFlow Auth Key", data)
        translator_name = "SiliconFlow_API"
        try:
            data = str(data)
            if len(data) >= 20:
                result = model.authenticationTranslatorSiliconFlowAuthKey(auth_key=data)
                if result is True:
                    key = data
                    auth_keys = config.AUTH_KEYS
                    auth_keys[translator_name] = key
                    config.AUTH_KEYS = auth_keys
                    config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = True
                    config.SELECTABLE_SILICONFLOW_MODEL_LIST = model.getTranslatorSiliconFlowModelList()
                    self.run(200, self.run_mapping["selectable_siliconflow_model_list"], config.SELECTABLE_SILICONFLOW_MODEL_LIST)
                    if config.SELECTED_SILICONFLOW_MODEL not in config.SELECTABLE_SILICONFLOW_MODEL_LIST:
                        config.SELECTED_SILICONFLOW_MODEL = config.SELECTABLE_SILICONFLOW_MODEL_LIST[0]
                    model.setTranslatorSiliconFlowModel(model=config.SELECTED_SILICONFLOW_MODEL)
                    self.run(200, self.run_mapping["selected_siliconflow_model"], config.SELECTED_SILICONFLOW_MODEL)
                    model.setTranslatorSiliconFlowAsrCorrection(config.SILICONFLOW_ENABLE_ASR_CORRECTION)
                    model.setTranslatorSiliconFlowEnableThinking(config.SILICONFLOW_ENABLE_THINKING)
                    model.setTranslatorSiliconFlowMaxTokens(config.SILICONFLOW_MAX_TOKENS)
                    model.setTranslatorSiliconFlowTemperature(config.SILICONFLOW_TEMPERATURE)
                    model.setTranslatorSiliconFlowCustomSystemPrompt(config.SILICONFLOW_CUSTOM_SYSTEM_PROMPT)
                    model.updateTranslatorSiliconFlowClient()
                    self.updateTranslationEngineAndEngineList()
                    response = {"status":200, "result":config.AUTH_KEYS[translator_name]}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.AUTH_SILICONFLOW_FAILED,
                        data=None
                    )
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.AUTH_SILICONFLOW_INVALID,
                    data=None
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=None
            )
        if response["status"] == 400:
            self.delSiliconFlowAuthKey()
        return response

    def delSiliconFlowAuthKey(self, *args, **kwargs) -> dict:
        translator_name = "SiliconFlow_API"
        auth_keys = config.AUTH_KEYS
        auth_keys[translator_name] = None
        config.AUTH_KEYS = auth_keys
        config.SELECTABLE_SILICONFLOW_MODEL_LIST = []
        config.SELECTED_SILICONFLOW_MODEL = None
        self.run(200, self.run_mapping["selectable_siliconflow_model_list"], config.SELECTABLE_SILICONFLOW_MODEL_LIST)
        self.run(200, self.run_mapping["selected_siliconflow_model"], config.SELECTED_SILICONFLOW_MODEL)
        config.SELECTABLE_TRANSLATION_ENGINE_STATUS[translator_name] = False
        self.updateTranslationEngineAndEngineList()
        return {"status":200, "result":config.AUTH_KEYS[translator_name]}

    def getSiliconFlowModelList(self, *args, **kwargs) -> dict:
        return {"status":200, "result": config.SELECTABLE_SILICONFLOW_MODEL_LIST}

    def getSiliconFlowModel(self, *args, **kwargs) -> dict:
        return {"status":200, "result":config.SELECTED_SILICONFLOW_MODEL}

    def setSiliconFlowModel(self, data, *args, **kwargs) -> dict:
        printLog("Set SiliconFlow Model", data)
        try:
            data = str(data)
            result = model.setTranslatorSiliconFlowModel(model=data)
            if result is True:
                config.SELECTED_SILICONFLOW_MODEL = data
                model.setTranslatorSiliconFlowModel(model=config.SELECTED_SILICONFLOW_MODEL)
                model.updateTranslatorSiliconFlowClient()
                response = {"status":200, "result":config.SELECTED_SILICONFLOW_MODEL}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.MODEL_SILICONFLOW_INVALID,
                    data=config.SELECTED_SILICONFLOW_MODEL
                )
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(
                e,
                data=config.SELECTED_SILICONFLOW_MODEL
            )
        return response

    # --- SiliconFlow extra params ---
    @staticmethod
    def getSiliconFlowAsrCorrection(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SILICONFLOW_ENABLE_ASR_CORRECTION}

    def setEnableSiliconFlowAsrCorrection(self, *args, **kwargs) -> dict:
        printLog("setEnableSiliconFlowAsrCorrection called, before:", config.SILICONFLOW_ENABLE_ASR_CORRECTION)
        try:
            config.SILICONFLOW_ENABLE_ASR_CORRECTION = True
            model.setTranslatorSiliconFlowAsrCorrection(True)
        except Exception:
            errorLogging()
        resp = {"status":200, "result":config.SILICONFLOW_ENABLE_ASR_CORRECTION}
        printLog("setEnableSiliconFlowAsrCorrection response:", resp)
        return resp

    def setDisableSiliconFlowAsrCorrection(self, *args, **kwargs) -> dict:
        printLog("setDisableSiliconFlowAsrCorrection called, before:", config.SILICONFLOW_ENABLE_ASR_CORRECTION)
        try:
            config.SILICONFLOW_ENABLE_ASR_CORRECTION = False
            model.setTranslatorSiliconFlowAsrCorrection(False)
        except Exception:
            errorLogging()
        resp = {"status":200, "result":config.SILICONFLOW_ENABLE_ASR_CORRECTION}
        printLog("setDisableSiliconFlowAsrCorrection response:", resp)
        return resp

    @staticmethod
    def getSiliconFlowEnableThinking(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SILICONFLOW_ENABLE_THINKING}

    def setEnableSiliconFlowEnableThinking(self, *args, **kwargs) -> dict:
        printLog("setEnableSiliconFlowEnableThinking called, before:", config.SILICONFLOW_ENABLE_THINKING)
        try:
            config.SILICONFLOW_ENABLE_THINKING = True
            model.setTranslatorSiliconFlowEnableThinking(True)
            model.updateTranslatorSiliconFlowClient()
        except Exception:
            errorLogging()
        resp = {"status":200, "result":config.SILICONFLOW_ENABLE_THINKING}
        printLog("setEnableSiliconFlowEnableThinking response:", resp)
        return resp

    def setDisableSiliconFlowEnableThinking(self, *args, **kwargs) -> dict:
        printLog("setDisableSiliconFlowEnableThinking called, before:", config.SILICONFLOW_ENABLE_THINKING)
        try:
            config.SILICONFLOW_ENABLE_THINKING = False
            model.setTranslatorSiliconFlowEnableThinking(False)
            model.updateTranslatorSiliconFlowClient()
        except Exception:
            errorLogging()
        resp = {"status":200, "result":config.SILICONFLOW_ENABLE_THINKING}
        printLog("setDisableSiliconFlowEnableThinking response:", resp)
        return resp

    @staticmethod
    def getSiliconFlowMaxTokens(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SILICONFLOW_MAX_TOKENS}

    def setSiliconFlowMaxTokens(self, data, *args, **kwargs) -> dict:
        try:
            config.SILICONFLOW_MAX_TOKENS = int(data)
            model.setTranslatorSiliconFlowMaxTokens(int(data))
            model.updateTranslatorSiliconFlowClient()
            return {"status":200, "result":config.SILICONFLOW_MAX_TOKENS}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.SILICONFLOW_MAX_TOKENS)

    @staticmethod
    def getSiliconFlowTemperature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SILICONFLOW_TEMPERATURE}

    def setSiliconFlowTemperature(self, data, *args, **kwargs) -> dict:
        try:
            config.SILICONFLOW_TEMPERATURE = float(data)
            model.setTranslatorSiliconFlowTemperature(float(data))
            model.updateTranslatorSiliconFlowClient()
            return {"status":200, "result":config.SILICONFLOW_TEMPERATURE}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.SILICONFLOW_TEMPERATURE)

    @staticmethod
    def getSiliconFlowCustomSystemPrompt(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SILICONFLOW_CUSTOM_SYSTEM_PROMPT}

    def setSiliconFlowCustomSystemPrompt(self, data, *args, **kwargs) -> dict:
        try:
            data = str(data)
            config.SILICONFLOW_CUSTOM_SYSTEM_PROMPT = data
            model.setTranslatorSiliconFlowCustomSystemPrompt(data)
            return {"status":200, "result":config.SILICONFLOW_CUSTOM_SYSTEM_PROMPT}
        except Exception as e:
            errorLogging()
            return VRCTError.create_exception_error_response(e, data=config.SILICONFLOW_CUSTOM_SYSTEM_PROMPT)

    def testSiliconFlowTranslation(self, data, *args, **kwargs) -> dict:
        printLog("Test SiliconFlow Translation", data)
        try:
            text = str(data.get("text", ""))
            input_lang = str(data.get("input_lang", ""))
            output_lang = str(data.get("output_lang", ""))
            if not text or not input_lang or not output_lang:
                raise Exception("Missing required fields: text, input_lang, output_lang")
            result = model.testTranslatorSiliconFlowTranslation(text, input_lang, output_lang)
            if result is False:
                raise Exception("SiliconFlow client is not connected")
            # Return detailed response for developer test panel
            corrected = model.getTranslatorSiliconFlowLastCorrectedSource()
            response = {
                "status": 200,
                "result": {
                    "translated": result,
                    "corrected_source": corrected if corrected else None,
                    "engine": "SiliconFlow_API",
                    "model": config.SELECTED_SILICONFLOW_MODEL,
                    "enable_thinking": config.SILICONFLOW_ENABLE_THINKING,
                    "enable_asr_correction": config.SILICONFLOW_ENABLE_ASR_CORRECTION,
                },
            }
        except Exception as e:
            errorLogging()
            response = VRCTError.create_exception_error_response(e, data=None)
        return response

    def testTranslationEngineDetailed(self, data, *args, **kwargs) -> dict:
        """Unified detailed test endpoint for all translation engines.

        Accepts: {engine, text, input_lang, output_lang, options: {enable_thinking, enable_asr_correction}}
        Returns detailed result with timing, raw output, and engine-specific info.
        """
        import time as _time
        printLog("testTranslationEngineDetailed", data)
        engine = str(data.get("engine", ""))
        text = str(data.get("text", ""))
        input_lang = str(data.get("input_lang", ""))
        output_lang = str(data.get("output_lang", ""))
        options = data.get("options", {}) or {}

        if not engine or not text or not input_lang or not output_lang:
            return {"status": 200, "result": {"error": "Missing required fields"}}

        start = _time.time()
        try:
            if engine == "SiliconFlow_API":
                # Temporarily apply options for this test
                orig_thinking = config.SILICONFLOW_ENABLE_THINKING
                orig_asr = config.SILICONFLOW_ENABLE_ASR_CORRECTION
                if "enable_thinking" in options:
                    config.SILICONFLOW_ENABLE_THINKING = bool(options["enable_thinking"])
                    model.setTranslatorSiliconFlowEnableThinking(bool(options["enable_thinking"]))
                if "enable_asr_correction" in options:
                    config.SILICONFLOW_ENABLE_ASR_CORRECTION = bool(options["enable_asr_correction"])
                    model.setTranslatorSiliconFlowAsrCorrection(bool(options["enable_asr_correction"]))
                if model.getTranslatorSiliconFlowConnected():
                    model.updateTranslatorSiliconFlowClient()

                result = model.testTranslatorSiliconFlowTranslation(text, input_lang, output_lang)
                elapsed = _time.time() - start
                corrected = model.getTranslatorSiliconFlowLastCorrectedSource()

                # Restore original options
                config.SILICONFLOW_ENABLE_THINKING = orig_thinking
                config.SILICONFLOW_ENABLE_ASR_CORRECTION = orig_asr
                model.setTranslatorSiliconFlowEnableThinking(orig_thinking)
                model.setTranslatorSiliconFlowAsrCorrection(orig_asr)
                if model.getTranslatorSiliconFlowConnected():
                    model.updateTranslatorSiliconFlowClient()

                if result is False:
                    return {"status": 200, "result": {"error": "SiliconFlow not connected"}}

                return {"status": 200, "result": {
                    "engine": engine,
                    "model": config.SELECTED_SILICONFLOW_MODEL,
                    "translated": result,
                    "corrected_source": corrected or None,
                    "elapsed_sec": round(elapsed, 3),
                    "options_used": {
                        "enable_thinking": bool(options.get("enable_thinking", orig_thinking)),
                        "enable_asr_correction": bool(options.get("enable_asr_correction", orig_asr)),
                        "temperature": config.SILICONFLOW_TEMPERATURE,
                        "max_tokens": config.SILICONFLOW_MAX_TOKENS,
                    },
                    "input": {"text": text, "input_lang": input_lang, "output_lang": output_lang},
                }}

            elif engine.startswith("Custom_OpenAI"):
                slot = engine.replace("Custom_OpenAI_API", "").replace("Custom_OpenAI", "")
                slot_num = int(slot) if slot.isdigit() else 1

                if slot_num == 1:
                    result = model.testTranslatorCustomOpenAITranslation(text, input_lang, output_lang)
                    model_name = config.CUSTOM_OPENAI_MODEL
                    api_url = config.CUSTOM_OPENAI_URL
                elif slot_num == 2:
                    result = model.testTranslatorCustomOpenAI2Translation(text, input_lang, output_lang)
                    model_name = config.CUSTOM_OPENAI_MODEL_2
                    api_url = config.CUSTOM_OPENAI_URL_2
                elif slot_num == 3:
                    result = model.testTranslatorCustomOpenAI3Translation(text, input_lang, output_lang)
                    model_name = config.CUSTOM_OPENAI_MODEL_3
                    api_url = config.CUSTOM_OPENAI_URL_3
                else:
                    return {"status": 200, "result": {"error": f"Unknown Custom OpenAI slot: {slot_num}"}}

                elapsed = _time.time() - start

                if result is False:
                    return {"status": 200, "result": {"error": f"Custom OpenAI {slot_num} not connected"}}

                return {"status": 200, "result": {
                    "engine": engine,
                    "model": model_name,
                    "api_url": api_url,
                    "translated": result,
                    "elapsed_sec": round(elapsed, 3),
                    "options_used": {},
                    "input": {"text": text, "input_lang": input_lang, "output_lang": output_lang},
                }}

            else:
                return {"status": 200, "result": {"error": f"Unsupported engine for test: {engine}"}}

        except Exception as e:
            errorLogging()
            elapsed = _time.time() - start
            return {"status": 200, "result": {
                "error": str(e),
                "engine": engine,
                "elapsed_sec": round(elapsed, 3),
            }}













    def getSendMessageFormatParts(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def setSendMessageFormatParts(data, *args, **kwargs) -> dict:
        config.SEND_MESSAGE_FORMAT_PARTS = dict(data)
        return {"status":200, "result":config.SEND_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def getReceivedMessageFormatParts(*args, **kwargs) -> dict:
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def setReceivedMessageFormatParts(data, *args, **kwargs) -> dict:
        config.RECEIVED_MESSAGE_FORMAT_PARTS = dict(data)
        return {"status":200, "result":config.RECEIVED_MESSAGE_FORMAT_PARTS}

    @staticmethod
    def getAutoClearMessageBox(*args, **kwargs) -> dict:
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setEnableAutoClearMessageBox(*args, **kwargs) -> dict:
        if config.AUTO_CLEAR_MESSAGE_BOX is False:
            config.AUTO_CLEAR_MESSAGE_BOX = True
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def setDisableAutoClearMessageBox(*args, **kwargs) -> dict:
        if config.AUTO_CLEAR_MESSAGE_BOX is True:
            config.AUTO_CLEAR_MESSAGE_BOX = False
        return {"status":200, "result":config.AUTO_CLEAR_MESSAGE_BOX}

    @staticmethod
    def getSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.SEND_ONLY_TRANSLATED_MESSAGES is False:
            config.SEND_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableSendOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.SEND_ONLY_TRANSLATED_MESSAGES is True:
            config.SEND_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.SEND_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getOverlaySmallLog(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setEnableOverlaySmallLog(*args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is False:
            if config.OVERLAY_LARGE_LOG is False:
                model.startOverlay()
            config.OVERLAY_SMALL_LOG = True
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def setDisableOverlaySmallLog(*args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is True:
            model.clearOverlayImageSmallLog()
            if config.OVERLAY_LARGE_LOG is False:
                model.shutdownOverlay()
            config.OVERLAY_SMALL_LOG = False
        return {"status":200, "result":config.OVERLAY_SMALL_LOG}

    @staticmethod
    def getOverlaySmallLogSettings(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def setOverlaySmallLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_SMALL_LOG_SETTINGS = data
        model.updateOverlaySmallLogSettings()
        return {"status":200, "result":config.OVERLAY_SMALL_LOG_SETTINGS}

    @staticmethod
    def getOverlayLargeLog(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setEnableOverlayLargeLog(*args, **kwargs) -> dict:
        if config.OVERLAY_LARGE_LOG is False:
            if config.OVERLAY_SMALL_LOG is False:
                model.startOverlay()
            config.OVERLAY_LARGE_LOG = True
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def setDisableOverlayLargeLog(*args, **kwargs) -> dict:
        if config.OVERLAY_LARGE_LOG is True:
            model.clearOverlayImageLargeLog()
            if config.OVERLAY_SMALL_LOG is False:
                model.shutdownOverlay()
            config.OVERLAY_LARGE_LOG = False
        return {"status":200, "result":config.OVERLAY_LARGE_LOG}

    @staticmethod
    def getOverlayLargeLogSettings(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_LARGE_LOG_SETTINGS}

    @staticmethod
    def setOverlayLargeLogSettings(data, *args, **kwargs) -> dict:
        config.OVERLAY_LARGE_LOG_SETTINGS = data
        model.updateOverlayLargeLogSettings()
        return {"status":200, "result":config.OVERLAY_LARGE_LOG_SETTINGS}

    @staticmethod
    def getOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setEnableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is False:
            config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = True
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def setDisableOverlayShowOnlyTranslatedMessages(*args, **kwargs) -> dict:
        if config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES is True:
            config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES = False
        return {"status":200, "result":config.OVERLAY_SHOW_ONLY_TRANSLATED_MESSAGES}

    @staticmethod
    def getSendMessageToVrc(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is False:
            config.SEND_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            config.SEND_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_MESSAGE_TO_VRC}

    @staticmethod
    def getSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setEnableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_RECEIVED_MESSAGE_TO_VRC is False:
            config.SEND_RECEIVED_MESSAGE_TO_VRC = True
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def setDisableSendReceivedMessageToVrc(*args, **kwargs) -> dict:
        if config.SEND_RECEIVED_MESSAGE_TO_VRC is True:
            config.SEND_RECEIVED_MESSAGE_TO_VRC = False
        return {"status":200, "result":config.SEND_RECEIVED_MESSAGE_TO_VRC}

    @staticmethod
    def getLoggerFeature(*args, **kwargs) -> dict:
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setEnableLoggerFeature(*args, **kwargs) -> dict:
        if config.LOGGER_FEATURE is False:
            model.startLogger()
            config.LOGGER_FEATURE = True
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def setDisableLoggerFeature(*args, **kwargs) -> dict:
        if config.LOGGER_FEATURE is True:
            model.stopLogger()
            config.LOGGER_FEATURE = False
        return {"status":200, "result":config.LOGGER_FEATURE}

    @staticmethod
    def getVrcMicMuteSync(*args, **kwargs) -> dict:
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    @staticmethod
    def setEnableVrcMicMuteSync(*args, **kwargs) -> dict:
        if config.VRC_MIC_MUTE_SYNC is False:
            if model.getIsOscQueryEnabled() is True:
                config.VRC_MIC_MUTE_SYNC = True
                model.setMuteSelfStatus()
                model.changeMicTranscriptStatus()
                response = {"status":200, "result":config.VRC_MIC_MUTE_SYNC}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED,
                    data=config.VRC_MIC_MUTE_SYNC
                )
        else:
            response = {"status":200, "result":config.VRC_MIC_MUTE_SYNC}
        return response

    @staticmethod
    def setDisableVrcMicMuteSync(*args, **kwargs) -> dict:
        if config.VRC_MIC_MUTE_SYNC is True:
            config.VRC_MIC_MUTE_SYNC = False
            model.changeMicTranscriptStatus()
        return {"status":200, "result":config.VRC_MIC_MUTE_SYNC}

    def setEnableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_RECEIVE is False:
            self.startThreadingCheckSpeakerEnergy()
            config.ENABLE_CHECK_ENERGY_RECEIVE = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setDisableCheckSpeakerThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_RECEIVE is True:
            self.stopThreadingCheckSpeakerEnergy()
            config.ENABLE_CHECK_ENERGY_RECEIVE = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_RECEIVE}

    def setEnableCheckMicThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_SEND is False:
            self.startThreadingCheckMicEnergy()
            config.ENABLE_CHECK_ENERGY_SEND = True
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    def setDisableCheckMicThreshold(self, *args, **kwargs) -> dict:
        if config.ENABLE_CHECK_ENERGY_SEND is True:
            self.stopThreadingCheckMicEnergy()
            config.ENABLE_CHECK_ENERGY_SEND = False
        return {"status":200, "result":config.ENABLE_CHECK_ENERGY_SEND}

    @staticmethod
    def openFilepathLogs(*args, **kwargs) -> dict:
        Popen(['explorer', config.PATH_LOGS.replace('/', '\\')], shell=True)
        return {"status":200, "result":True}

    @staticmethod
    def openFilepathConfigFile(*args, **kwargs) -> dict:
        Popen(['explorer', config.PATH_LOCAL.replace('/', '\\')], shell=True)
        return {"status":200, "result":True}

    def setEnableTranscriptionSend(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_SEND is False:
            self.startThreadingTranscriptionSendMessage()
            config.ENABLE_TRANSCRIPTION_SEND = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setDisableTranscriptionSend(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_SEND is True:
            self.stopThreadingTranscriptionSendMessage()
            config.ENABLE_TRANSCRIPTION_SEND = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_SEND}

    def setEnableTranscriptionReceive(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is False:
            self.startThreadingTranscriptionReceiveMessage()
            config.ENABLE_TRANSCRIPTION_RECEIVE = True
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def setDisableTranscriptionReceive(self, *args, **kwargs) -> dict:
        if config.ENABLE_TRANSCRIPTION_RECEIVE is True:
            self.stopThreadingTranscriptionReceiveMessage()
            config.ENABLE_TRANSCRIPTION_RECEIVE = False
        return {"status":200, "result":config.ENABLE_TRANSCRIPTION_RECEIVE}

    def webviewTranscriptionResult(self, data, *args, **kwargs) -> dict:
        """Handle speech recognition results from the frontend WebView (Web Speech API)."""
        printLog("webviewTranscriptionResult received:", data)
        if not data or not isinstance(data, dict):
            return {"status":400, "result":"Invalid webview transcription data"}
        text = data.get("text", "")
        language = data.get("language", None)
        is_final = data.get("is_final", True)
        if not text or not is_final:
            return {"status":200, "result":True}

        # Resolve language from config if not provided by the frontend
        if language is None:
            selected = config.SELECTED_YOUR_LANGUAGES.get(config.SELECTED_TAB_NO, {})
            first_lang = next(
                (v for v in selected.values() if v.get("enable")),
                None,
            )
            if first_lang:
                language = first_lang.get("language", None)

        # Feed into the same pipeline as mic transcription
        result = {"text": text, "language": language}
        try:
            self.micMessage(result)
        except Exception:
            errorLogging()
        return {"status":200, "result":True}

    def sendMessageBox(self, data, *args, **kwargs) -> dict:
        response = self.chatMessage(data)
        return response

    @staticmethod
    def typingMessageBox(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStartSendTyping()
        return {"status":200, "result":True}

    @staticmethod
    def stopTypingMessageBox(*args, **kwargs) -> dict:
        if config.SEND_MESSAGE_TO_VRC is True:
            model.oscStopSendTyping()
        return {"status":200, "result":True}

    @staticmethod
    def sendTextOverlay(data, *args, **kwargs) -> dict:
        if config.OVERLAY_SMALL_LOG is True:
            if model.overlay.initialized is True:
                overlay_image = model.createOverlayImageSmallMessage(data)
                model.updateOverlaySmallLog(overlay_image)

        if config.OVERLAY_LARGE_LOG is True:
            if model.overlay.initialized is True:
                overlay_image = model.createOverlayImageLargeMessage(data)
                model.updateOverlayLargeLog(overlay_image)
        return {"status":200, "result":data}

    @staticmethod
    def getTelemetry(*args, **kwargs) -> dict:
        return {"status":200, "result":config.ENABLE_TELEMETRY}

    @staticmethod
    def setEnableTelemetry(*args, **kwargs) -> dict:
        if config.ENABLE_TELEMETRY is False:
            config.ENABLE_TELEMETRY = True
            model.telemetryInit(enabled=True, app_version=config.VERSION)
        return {"status":200, "result":config.ENABLE_TELEMETRY}

    @staticmethod
    def setDisableTelemetry(*args, **kwargs) -> dict:
        if config.ENABLE_TELEMETRY is True:
            config.ENABLE_TELEMETRY = False
            model.telemetryShutdown()
        return {"status":200, "result":config.ENABLE_TELEMETRY}

    def swapYourLanguageAndTargetLanguage(self, *args, **kwargs) -> dict:
        your_languages = config.SELECTED_YOUR_LANGUAGES
        your_language_temp = your_languages[config.SELECTED_TAB_NO]["1"]

        target_languages = config.SELECTED_TARGET_LANGUAGES
        target_language_temp = target_languages[config.SELECTED_TAB_NO]["1"]

        your_languages[config.SELECTED_TAB_NO]["1"] = target_language_temp
        target_languages[config.SELECTED_TAB_NO]["1"] = your_language_temp

        self.setSelectedYourLanguages(your_languages)
        self.setSelectedTargetLanguages(target_languages)
        return {
            "status":200,
            "result":{
                "your":config.SELECTED_YOUR_LANGUAGES,
                "target":config.SELECTED_TARGET_LANGUAGES,
                }
            }

    def updateSoftware(self, *args, **kwargs) -> dict:
        th_start_update_software = Thread(target=model.updateSoftware)
        th_start_update_software.daemon = True
        th_start_update_software.start()
        return {"status":200, "result":True}



    def messageFormatter(format_type:str, translation:list, message:str) -> str:
        if format_type == "RECEIVED":
            format_parts = config.RECEIVED_MESSAGE_FORMAT_PARTS
        elif format_type == "SEND":
            format_parts = config.SEND_MESSAGE_FORMAT_PARTS
        else:
            raise ValueError("format_type is not found", format_type)

        message_part = format_parts["message"]["prefix"] + message + format_parts["message"]["suffix"]
        translation_part = format_parts["translation"]["prefix"] + format_parts["translation"]["separator"].join(translation) + format_parts["translation"]["suffix"]

        if len(translation) > 0 and message != "":
            # 翻訳とメッセージの順序を決定
            if format_parts["translation_first"]:
                osc_message = translation_part + format_parts["separator"] + message_part
            else:
                osc_message = message_part + format_parts["separator"] + translation_part
        elif len(translation) > 0 and message == "":
            osc_message = translation_part
        else:
            osc_message = message_part
        return osc_message


    def startTranscriptionSendMessage(self) -> None:
        # WebView engine handles speech recognition in the frontend; no mic recording needed
        if config.SELECTED_TRANSCRIPTION_ENGINE == "WebView":
            printLog("Transcription engine is WebView — skipping mic recording, frontend handles speech recognition")
            return
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        try:
            model.startMicTranscript(self.micMessage)
        except Exception:
            errorLogging()
        finally:
            self.device_access_status = True

    @staticmethod
    def stopTranscriptionSendMessage() -> None:
        model.stopMicTranscript()

    def startThreadingTranscriptionSendMessage(self) -> None:
        th_startTranscriptionSendMessage = Thread(target=self.startTranscriptionSendMessage)
        th_startTranscriptionSendMessage.daemon = True
        th_startTranscriptionSendMessage.start()

    def stopThreadingTranscriptionSendMessage(self) -> None:
        th_stopTranscriptionSendMessage = Thread(target=self.stopTranscriptionSendMessage)
        th_stopTranscriptionSendMessage.daemon = True
        th_stopTranscriptionSendMessage.start()
        th_stopTranscriptionSendMessage.join()

    def startTranscriptionReceiveMessage(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        try:
            model.startSpeakerTranscript(self.speakerMessage)
        except Exception:
            errorLogging()
        finally:
            self.device_access_status = True

    @staticmethod
    def stopTranscriptionReceiveMessage() -> None:
        model.stopSpeakerTranscript()

    def startThreadingTranscriptionReceiveMessage(self) -> None:
        th_startTranscriptionReceiveMessage = Thread(target=self.startTranscriptionReceiveMessage)
        th_startTranscriptionReceiveMessage.daemon = True
        th_startTranscriptionReceiveMessage.start()

    def stopThreadingTranscriptionReceiveMessage(self) -> None:
        th_stopTranscriptionReceiveMessage = Thread(target=self.stopTranscriptionReceiveMessage)
        th_stopTranscriptionReceiveMessage.daemon = True
        th_stopTranscriptionReceiveMessage.start()
        th_stopTranscriptionReceiveMessage.join()

    @staticmethod
    def replaceExclamationsWithRandom(text):
        # ![...] にマッチする正規表現
        pattern = r'!\[(.*?)\]'

        # 乱数と置換部分を保存する辞書
        replacement_dict = {}

        num = 4096
        # マッチした部分を4096から始まる整数に置換する。置換毎に4097, 4098, ... と増える
        def replace(match):
            original = match.group(1)
            nonlocal num
            rand_value = hex(num)
            replacement_dict[rand_value] = original
            num += 1
            return f" ${rand_value} "

        # 文章内の ![] の部分を置換
        replaced_text = re.sub(pattern, replace, text)

        return replaced_text, replacement_dict

    @staticmethod
    def restoreText(escaped_text, escape_dict):
        # 大文字小文字を無視して置換するために、正規表現を使う
        for escape_seq, char in escape_dict.items():
            # escaped_text の部分を pattern で置換
            pattern = re.escape(f"${escape_seq}") + r"|\$\s+" + re.escape(escape_seq)
            escaped_text = re.sub(pattern, char, escaped_text, flags=re.IGNORECASE)
        return escaped_text

    @staticmethod
    def removeExclamations(text):
        # ![...] を [...] に置換する正規表現
        pattern = r'!\[(.*?)\]'
        # ![...] の部分を [] 内のテキストに置換
        cleaned_text = re.sub(pattern, r'\1', text)
        return cleaned_text


    def updateTranslationEngineAndEngineList(self):
        engines = config.SELECTED_TRANSLATION_ENGINES
        engine = engines[config.SELECTED_TAB_NO]
        selectable_engines = self.getTranslationEngines()["result"]
        if engine not in selectable_engines and len(selectable_engines) > 0:
            engine = selectable_engines[0]
        engines[config.SELECTED_TAB_NO] = engine
        config.SELECTED_TRANSLATION_ENGINES = engines

        self.run(200, self.run_mapping["selected_translation_engines"], config.SELECTED_TRANSLATION_ENGINES)
        self.run(200, self.run_mapping["translation_engines"], selectable_engines)



    def startCheckMicEnergy(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        model.startCheckMicEnergy(self.progressBarMicEnergy)
        self.device_access_status = True

    def startThreadingCheckMicEnergy(self) -> None:
        th_startCheckMicEnergy = Thread(target=self.startCheckMicEnergy)
        th_startCheckMicEnergy.daemon = True
        th_startCheckMicEnergy.start()

    def stopCheckMicEnergy(self) -> None:
        model.stopCheckMicEnergy()

    def stopThreadingCheckMicEnergy(self) -> None:
        th_stopCheckMicEnergy = Thread(target=self.stopCheckMicEnergy)
        th_stopCheckMicEnergy.daemon = True
        th_stopCheckMicEnergy.start()
        th_stopCheckMicEnergy.join()

    def startCheckSpeakerEnergy(self) -> None:
        while self.device_access_status is False:
            sleep(1)
        self.device_access_status = False
        model.startCheckSpeakerEnergy(self.progressBarSpeakerEnergy)
        self.device_access_status = True

    def startThreadingCheckSpeakerEnergy(self) -> None:
        th_startCheckSpeakerEnergy = Thread(target=self.startCheckSpeakerEnergy)
        th_startCheckSpeakerEnergy.daemon = True
        th_startCheckSpeakerEnergy.start()

    def stopCheckSpeakerEnergy(self) -> None:
        model.stopCheckSpeakerEnergy()

    def stopThreadingCheckSpeakerEnergy(self) -> None:
        th_stopCheckSpeakerEnergy = Thread(target=self.stopCheckSpeakerEnergy)
        th_stopCheckSpeakerEnergy.daemon = True
        th_stopCheckSpeakerEnergy.start()
        th_stopCheckSpeakerEnergy.join()

    def startWatchdog(*args, **kwargs) -> dict:
        model.startWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def feedWatchdog(*args, **kwargs) -> dict:
        model.feedWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def setWatchdogCallback(callback) -> dict:
        model.setWatchdogCallback(callback)
        return {"status":200, "result":True}

    @staticmethod
    def stopWatchdog(*args, **kwargs) -> dict:
        model.stopWatchdog()
        return {"status":200, "result":True}

    @staticmethod
    def getWebSocketHost(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WEBSOCKET_HOST}

    @staticmethod
    def setWebSocketHost(data, *args, **kwargs) -> dict:
        if isValidIpAddress(data) is False:
            response = VRCTError.create_error_response(
                ErrorCode.VALIDATION_INVALID_IP,
                data=config.WEBSOCKET_HOST
            )
        else:
            if model.checkWebSocketServerAlive() is False:
                config.WEBSOCKET_HOST = data
                response = {"status":200, "result":config.WEBSOCKET_HOST}
            else:
                if data == config.WEBSOCKET_HOST:
                    response = {"status":200, "result":config.WEBSOCKET_HOST}
                elif isAvailableWebSocketServer(data, config.WEBSOCKET_PORT):
                    model.stopWebSocketServer()
                    model.startWebSocketServer(data, config.WEBSOCKET_PORT)
                    config.WEBSOCKET_HOST = data
                    response = {"status":200, "result":config.WEBSOCKET_HOST}
                else:
                    response = VRCTError.create_error_response(
                        ErrorCode.WEBSOCKET_HOST_UNAVAILABLE,
                        data=config.WEBSOCKET_HOST
                    )

        return response

    @staticmethod
    def getWebSocketPort(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WEBSOCKET_PORT}

    @staticmethod
    def setWebSocketPort(data, *args, **kwargs) -> dict:
        if model.checkWebSocketServerAlive() is False:
            config.WEBSOCKET_PORT = int(data)
            response = {"status":200, "result":config.WEBSOCKET_PORT}
        else:
            if int(data) == config.WEBSOCKET_PORT:
                return {"status":200, "result":config.WEBSOCKET_PORT}
            elif isAvailableWebSocketServer(config.WEBSOCKET_HOST, int(data)) is True:
                model.stopWebSocketServer()
                model.startWebSocketServer(config.WEBSOCKET_HOST, int(data))
                config.WEBSOCKET_PORT = int(data)
                response = {"status":200, "result":config.WEBSOCKET_PORT}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.WEBSOCKET_PORT_UNAVAILABLE,
                    data=config.WEBSOCKET_PORT
                )
        return response

    @staticmethod
    def getWebSocketServer(*args, **kwargs) -> dict:
        return {"status":200, "result":config.WEBSOCKET_SERVER}

    @staticmethod
    def setEnableWebSocketServer(*args, **kwargs) -> dict:
        if config.WEBSOCKET_SERVER is False:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
                config.WEBSOCKET_SERVER = True
                response = {"status":200, "result":config.WEBSOCKET_SERVER}
            else:
                response = VRCTError.create_error_response(
                    ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE,
                    data=config.WEBSOCKET_SERVER
                )
        else:
            response = {"status":200, "result":config.WEBSOCKET_SERVER}
        return response

    @staticmethod
    def setDisableWebSocketServer(*args, **kwargs) -> dict:
        if config.WEBSOCKET_SERVER is True:
            config.WEBSOCKET_SERVER = False
            model.stopWebSocketServer()
        return {"status":200, "result":config.WEBSOCKET_SERVER}

    # Clipboard control
    @staticmethod
    def getClipboard(*args, **kwargs) -> dict:
        return {"status":200, "result":config.ENABLE_CLIPBOARD}

    @staticmethod
    def setEnableClipboard(*args, **kwargs) -> dict:
        if config.ENABLE_CLIPBOARD is False:
            config.ENABLE_CLIPBOARD = True
        return {"status":200, "result":config.ENABLE_CLIPBOARD}

    @staticmethod
    def setDisableClipboard(*args, **kwargs) -> dict:
        if config.ENABLE_CLIPBOARD is True:
            config.ENABLE_CLIPBOARD = False
        return {"status":200, "result":config.ENABLE_CLIPBOARD}

    def initializationProgress(self, progress):
        self.run(200, self.run_mapping["initialization_progress"], progress)

    def enableOscQuery(self):
        self.run(
            200,
            self.run_mapping["enable_osc_query"],
            {
                "data": True,
                "disabled_functions": []
            }
        )

    def disableOscQuery(self, mute_sync_info:bool=False):
        disabled_functions = []
        if mute_sync_info is True:
            disabled_functions.append("vrc_mic_mute_sync")
        self.run(200, self.run_mapping["enable_osc_query"], {
            "data": False,
            "disabled_functions": disabled_functions
        })

    def init(self, *args, **kwargs) -> None:
        removeLog()
        printLog("Start Initialization")

        # Check network connectivity
        connected_network = isConnectedNetwork()
        if connected_network is True:
            self.connectedNetwork()
        else:
            self.disconnectedNetwork()
        printLog(f"Connected Network: {connected_network}")

        self.initializationProgress(1)

        # Init Translation Engine Status (API-only, no local models)
        printLog("Init Translation Engine Status (fast)")
        for engine in config.SELECTABLE_TRANSLATION_ENGINE_LIST:
            if engine in config.AUTH_KEYS and config.AUTH_KEYS.get(engine) is not None:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = True
            elif engine.startswith("Custom_OpenAI_API"):
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = True
            else:
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = False

        # Init Transcription Engine Status
        for engine in config.SELECTABLE_TRANSCRIPTION_ENGINE_LIST:
            config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = True

        self.initializationProgress(2)

        # Set Translation Engine
        printLog("Set Translation Engine")
        self.updateTranslationEngineAndEngineList()

        self.initializationProgress(3)

        # Set Word Filter
        printLog("Set Word Filter")
        model.addKeywords()

        # Init Logger
        printLog("Init Logger")
        if config.LOGGER_FEATURE is True:
            model.startLogger()

        self.initializationProgress(4)

        # Init OSC Receive (Background) — kept for VRChat connectivity
        printLog("Init OSC Receive (Background)")

        def init_osc_receive_background():
            try:
                model.startReceiveOSC()
                osc_query_enabled = model.getIsOscQueryEnabled()
                if osc_query_enabled is True:
                    self.enableOscQuery()
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self.setEnableVrcMicMuteSync()
                else:
                    mute_sync_info_flag = False
                    if config.VRC_MIC_MUTE_SYNC is True:
                        self.setDisableVrcMicMuteSync()
                        mute_sync_info_flag = True
                    self.disableOscQuery(mute_sync_info=mute_sync_info_flag)
                printLog("[Background] OSC Receive initialization completed")
            except Exception:
                errorLogging()
                printLog("[Background] OSC Receive initialization failed")

        bg_thread = Thread(target=init_osc_receive_background)
        bg_thread.daemon = True
        bg_thread.start()

        # Init Device Manager
        printLog("Init Device Manager")
        device_manager.setCallbackHostList(self.updateMicHostList)
        device_manager.setCallbackMicDeviceList(self.updateMicDeviceList)
        device_manager.setCallbackSpeakerDeviceList(self.updateSpeakerDeviceList)

        printLog("Init Auto Device Selection")
        if config.AUTO_MIC_SELECT is True:
            self.applyAutoMicSelect()
        if config.AUTO_SPEAKER_SELECT is True:
            self.applyAutoSpeakerSelect()

        # Init Overlay
        printLog("Init Overlay")
        if (config.OVERLAY_SMALL_LOG is True or config.OVERLAY_LARGE_LOG is True):
            model.startOverlay()

        # Init WebSocket Server
        printLog("Init WebSocket Server")
        if config.WEBSOCKET_SERVER is True:
            if isAvailableWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT) is True:
                model.startWebSocketServer(config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
            else:
                config.WEBSOCKET_SERVER = False
                model.stopWebSocketServer()
                printLog("WebSocket server host or port is not available")

        # Revalidate Selected Models
        printLog("Revalidate Selected Models")
        config.revalidate_selected_models()

        # Update Settings
        printLog("Update settings")
        self.updateConfigSettings()

        printLog("End Initialization")
        self.startWatchdog()

        # === Deferred background tasks (after UI is responsive) ===
        def deferred_background_init():
            try:
                actual_connected = connected_network
                printLog(f"[Background] Network status: {actual_connected}")
                if not actual_connected:
                    self.disconnectedNetwork()
                    for engine in config.SELECTABLE_TRANSLATION_ENGINE_LIST:
                        if not engine.startswith("Custom_OpenAI_API"):
                            config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = False
                    for engine in config.SELECTABLE_TRANSCRIPTION_ENGINE_LIST:
                        if engine != "WebView":
                            config.SELECTABLE_TRANSCRIPTION_ENGINE_STATUS[engine] = False

                # Verify API engines in background
                self._verifyEnginesBackground(actual_connected)

                # Transliteration (if enabled)
                if config.CONVERT_MESSAGE_TO_ROMAJI is True or config.CONVERT_MESSAGE_TO_HIRAGANA is True:
                    model.startTransliteration()
                    printLog("[Background] Transliteration loaded")

                printLog("[Background] Deferred init completed")
            except Exception:
                errorLogging()
                printLog("[Background] Deferred init failed")

        bg_deferred = Thread(target=deferred_background_init)
        bg_deferred.daemon = True
        bg_deferred.start()

    def _verifyEnginesBackground(self, connected_network: bool) -> None:
        """Background verification of translation engine auth keys and model lists."""

        def check_engine(engine: str) -> tuple:
            status = False
            auth_key_invalid = False
            model_list = None
            selected_model = None
            try:
                match engine:
                    case "DeepL_API":
                        if config.AUTH_KEYS.get(engine) is None:
                            status = False
                        elif model.authenticationTranslatorDeepLAuthKey(auth_key=config.AUTH_KEYS[engine]):
                            status = True
                        else:
                            auth_key_invalid = True
                    case "Gemini_API":
                        if config.AUTH_KEYS.get(engine) is None:
                            status = False
                        elif model.authenticationTranslatorGeminiAuthKey(auth_key=config.AUTH_KEYS[engine]):
                            model_list = model.getTranslatorGeminiModelList()
                            selected_model = config.SELECTED_GEMINI_MODEL if config.SELECTED_GEMINI_MODEL in model_list else model_list[0]
                            status = True
                        else:
                            auth_key_invalid = True
                    case "OpenAI_API":
                        if config.AUTH_KEYS.get(engine) is None:
                            status = False
                        elif model.authenticationTranslatorOpenAIAuthKey(auth_key=config.AUTH_KEYS[engine]):
                            model_list = model.getTranslatorOpenAIModelList()
                            selected_model = config.SELECTED_OPENAI_MODEL if config.SELECTED_OPENAI_MODEL in model_list else model_list[0]
                            status = True
                        else:
                            auth_key_invalid = True
                    case "SiliconFlow_API":
                        if config.AUTH_KEYS.get(engine) is None:
                            status = False
                        elif model.authenticationTranslatorSiliconFlowAuthKey(auth_key=config.AUTH_KEYS[engine]):
                            model_list = model.getTranslatorSiliconFlowModelList()
                            selected_model = config.SELECTED_SILICONFLOW_MODEL if config.SELECTED_SILICONFLOW_MODEL in model_list else model_list[0]
                            status = True
                        else:
                            auth_key_invalid = True
                    case _:
                        status = connected_network is True
            except Exception as e:
                printLog(f"[Background] Error checking engine {engine}: {str(e)}")
                errorLogging()
            return engine, status, auth_key_invalid, model_list, selected_model

        engines_to_check = list(config.SELECTABLE_TRANSLATION_ENGINE_LIST)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(check_engine, e): e for e in engines_to_check}
            for future in as_completed(futures):
                engine, status, auth_key_invalid, model_list, selected_model = future.result()
                config.SELECTABLE_TRANSLATION_ENGINE_STATUS[engine] = status

                if auth_key_invalid:
                    auth_keys = config.AUTH_KEYS
                    auth_keys[engine] = None
                    config.AUTH_KEYS = auth_keys
                    printLog(f"[Background] {engine} auth key is invalid")

                if model_list is not None and status:
                    match engine:
                        case "Gemini_API":
                            config.SELECTABLE_GEMINI_MODEL_LIST = model_list
                            config.SELECTED_GEMINI_MODEL = selected_model
                            model.setTranslatorGeminiModel(selected_model)
                            model.updateTranslatorGeminiClient()
                        case "OpenAI_API":
                            config.SELECTABLE_OPENAI_MODEL_LIST = model_list
                            config.SELECTED_OPENAI_MODEL = selected_model
                            model.setTranslatorOpenAIModel(selected_model)
                            model.updateTranslatorOpenAIClient()
                        case "SiliconFlow_API":
                            config.SELECTABLE_SILICONFLOW_MODEL_LIST = model_list
                            config.SELECTED_SILICONFLOW_MODEL = selected_model
                            model.setTranslatorSiliconFlowModel(selected_model)
                            model.setTranslatorSiliconFlowAsrCorrection(config.SILICONFLOW_ENABLE_ASR_CORRECTION)
                            model.setTranslatorSiliconFlowEnableThinking(config.SILICONFLOW_ENABLE_THINKING)
                            model.setTranslatorSiliconFlowMaxTokens(config.SILICONFLOW_MAX_TOKENS)
                            model.setTranslatorSiliconFlowTemperature(config.SILICONFLOW_TEMPERATURE)
                            model.setTranslatorSiliconFlowCustomSystemPrompt(config.SILICONFLOW_CUSTOM_SYSTEM_PROMPT)
                            model.updateTranslatorSiliconFlowClient()

                printLog(f"[Background] {engine} verified: {status}")

        # Update frontend with verified results
        self.updateTranslationEngineAndEngineList()
        printLog("[Background] Engine verification completed")

