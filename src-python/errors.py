# src-python/errors.py
"""
統一エラー管理システム (Lightweight WebView-only build)

すべてのエラーを一元管理し、エンドポイントとエラーコードの対応を明確にする。
"""

from typing import Any, Optional, Dict
from enum import Enum


class ErrorCode(str, Enum):
    """エラーコード定数"""
    # デバイス関連エラー
    DEVICE_NO_MIC = "DEVICE_NO_MIC"
    DEVICE_NO_SPEAKER = "DEVICE_NO_SPEAKER"

    # 翻訳関連エラー
    TRANSLATION_ENGINE_LIMIT = "TRANSLATION_ENGINE_LIMIT"

    # バリデーションエラー
    VALIDATION_MIC_THRESHOLD = "VALIDATION_MIC_THRESHOLD"
    VALIDATION_SPEAKER_THRESHOLD = "VALIDATION_SPEAKER_THRESHOLD"
    VALIDATION_MIC_RECORD_TIMEOUT = "VALIDATION_MIC_RECORD_TIMEOUT"
    VALIDATION_MIC_PHRASE_TIMEOUT = "VALIDATION_MIC_PHRASE_TIMEOUT"
    VALIDATION_MIC_MAX_PHRASES = "VALIDATION_MIC_MAX_PHRASES"
    VALIDATION_SPEAKER_RECORD_TIMEOUT = "VALIDATION_SPEAKER_RECORD_TIMEOUT"
    VALIDATION_SPEAKER_PHRASE_TIMEOUT = "VALIDATION_SPEAKER_PHRASE_TIMEOUT"
    VALIDATION_SPEAKER_MAX_PHRASES = "VALIDATION_SPEAKER_MAX_PHRASES"
    VALIDATION_INVALID_IP = "VALIDATION_INVALID_IP"
    VALIDATION_CANNOT_SET_IP = "VALIDATION_CANNOT_SET_IP"

    # 認証エラー
    AUTH_DEEPL_LENGTH = "AUTH_DEEPL_LENGTH"
    AUTH_DEEPL_FAILED = "AUTH_DEEPL_FAILED"
    AUTH_GEMINI_LENGTH = "AUTH_GEMINI_LENGTH"
    AUTH_GEMINI_FAILED = "AUTH_GEMINI_FAILED"
    AUTH_OPENAI_INVALID = "AUTH_OPENAI_INVALID"
    AUTH_OPENAI_FAILED = "AUTH_OPENAI_FAILED"
    AUTH_SILICONFLOW_INVALID = "AUTH_SILICONFLOW_INVALID"
    AUTH_SILICONFLOW_FAILED = "AUTH_SILICONFLOW_FAILED"

    # モデル選択エラー
    MODEL_GEMINI_INVALID = "MODEL_GEMINI_INVALID"
    MODEL_OPENAI_INVALID = "MODEL_OPENAI_INVALID"
    MODEL_SILICONFLOW_INVALID = "MODEL_SILICONFLOW_INVALID"

    # 接続エラー
    CONNECTION_CUSTOM_OPENAI_FAILED = "CONNECTION_CUSTOM_OPENAI_FAILED"
    CONNECTION_CUSTOM_OPENAI_2_FAILED = "CONNECTION_CUSTOM_OPENAI_2_FAILED"
    CONNECTION_CUSTOM_OPENAI_3_FAILED = "CONNECTION_CUSTOM_OPENAI_3_FAILED"

    # WebSocketエラー
    WEBSOCKET_HOST_INVALID = "WEBSOCKET_HOST_INVALID"
    WEBSOCKET_PORT_UNAVAILABLE = "WEBSOCKET_PORT_UNAVAILABLE"
    WEBSOCKET_SERVER_UNAVAILABLE = "WEBSOCKET_SERVER_UNAVAILABLE"

    # VRC連携エラー
    VRC_MIC_MUTE_SYNC_OSC_DISABLED = "VRC_MIC_MUTE_SYNC_OSC_DISABLED"

    # 汎用エラー
    GENERAL_EXCEPTION = "GENERAL_EXCEPTION"
    GENERAL_UNKNOWN = "GENERAL_UNKNOWN"


class ErrorCategory(str, Enum):
    """エラーカテゴリ"""
    DEVICE = "device"
    TRANSLATION = "translation"
    VALIDATION = "validation"
    AUTH = "auth"
    MODEL = "model"
    CONNECTION = "connection"
    WEBSOCKET = "websocket"
    VRC = "vrc"
    GENERAL = "general"


ERROR_METADATA: Dict[ErrorCode, Dict[str, Any]] = {
    ErrorCode.DEVICE_NO_MIC: {
        "category": ErrorCategory.DEVICE,
        "message": "No mic device detected",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.DEVICE_NO_SPEAKER: {
        "category": ErrorCategory.DEVICE,
        "message": "No speaker device detected",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.TRANSLATION_ENGINE_LIMIT: {
        "category": ErrorCategory.TRANSLATION,
        "message": "Translation engine limit error",
        "severity": "warning",
        "user_action_required": False,
        "auto_fallback": True,
    },
    ErrorCode.VALIDATION_MIC_THRESHOLD: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic energy threshold value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_THRESHOLD: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker energy threshold value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic record timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic phrase timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_MIC_MAX_PHRASES: {
        "category": ErrorCategory.VALIDATION,
        "message": "Mic max phrases value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker record timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker phrase timeout value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES: {
        "category": ErrorCategory.VALIDATION,
        "message": "Speaker max phrases value is out of range",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_INVALID_IP: {
        "category": ErrorCategory.VALIDATION,
        "message": "Invalid IP address",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.VALIDATION_CANNOT_SET_IP: {
        "category": ErrorCategory.VALIDATION,
        "message": "Cannot set IP address",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_DEEPL_LENGTH: {
        "category": ErrorCategory.AUTH,
        "message": "DeepL auth key length is not correct",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_DEEPL_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of deepL auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_GEMINI_LENGTH: {
        "category": ErrorCategory.AUTH,
        "message": "Gemini auth key length is not correct",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_GEMINI_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of gemini auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_OPENAI_INVALID: {
        "category": ErrorCategory.AUTH,
        "message": "OpenAI auth key is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_OPENAI_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of OpenAI auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.AUTH_SILICONFLOW_INVALID: {
        "category": ErrorCategory.AUTH,
        "message": "SiliconFlow auth key is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.AUTH_SILICONFLOW_FAILED: {
        "category": ErrorCategory.AUTH,
        "message": "Authentication failure of SiliconFlow auth key",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.MODEL_GEMINI_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "Gemini model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_OPENAI_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "OpenAI model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.MODEL_SILICONFLOW_INVALID: {
        "category": ErrorCategory.MODEL,
        "message": "SiliconFlow model is not valid",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.CONNECTION_CUSTOM_OPENAI_FAILED: {
        "category": ErrorCategory.CONNECTION,
        "message": "Cannot connect to Custom OpenAI endpoint",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.CONNECTION_CUSTOM_OPENAI_2_FAILED: {
        "category": ErrorCategory.CONNECTION,
        "message": "Cannot connect to Custom OpenAI 2 endpoint",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.CONNECTION_CUSTOM_OPENAI_3_FAILED: {
        "category": ErrorCategory.CONNECTION,
        "message": "Cannot connect to Custom OpenAI 3 endpoint",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.WEBSOCKET_HOST_INVALID: {
        "category": ErrorCategory.WEBSOCKET,
        "message": "WebSocket server host is not available",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.WEBSOCKET_PORT_UNAVAILABLE: {
        "category": ErrorCategory.WEBSOCKET,
        "message": "WebSocket server port is not available",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE: {
        "category": ErrorCategory.WEBSOCKET,
        "message": "WebSocket server host or port is not available",
        "severity": "error",
        "user_action_required": True,
    },
    ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED: {
        "category": ErrorCategory.VRC,
        "message": "Cannot enable VRC mic mute sync while OSC query is disabled",
        "severity": "warning",
        "user_action_required": True,
    },
    ErrorCode.GENERAL_EXCEPTION: {
        "category": ErrorCategory.GENERAL,
        "message": "An error occurred",
        "severity": "error",
        "user_action_required": False,
    },
    ErrorCode.GENERAL_UNKNOWN: {
        "category": ErrorCategory.GENERAL,
        "message": "Unknown error",
        "severity": "error",
        "user_action_required": False,
    },
}


class VRCTError:
    """VRCTエラーハンドリングクラス"""

    @staticmethod
    def create_error_response(
        error_code: ErrorCode,
        data: Any = None,
        details: Optional[Dict[str, Any]] = None,
        custom_message: Optional[str] = None
    ) -> Dict[str, Any]:
        metadata = ERROR_METADATA.get(error_code, ERROR_METADATA[ErrorCode.GENERAL_UNKNOWN])
        return {
            "status": 400,
            "result": {
                "error_code": error_code.value,
                "message": custom_message or metadata["message"],
                "data": data,
                "details": details or {},
                "category": metadata["category"].value,
                "severity": metadata["severity"],
            }
        }

    @staticmethod
    def create_exception_error_response(
        exception: Exception,
        data: Any = None,
        error_code: ErrorCode = ErrorCode.GENERAL_EXCEPTION
    ) -> Dict[str, Any]:
        return VRCTError.create_error_response(
            error_code=error_code,
            data=data,
            custom_message=f"Error: {str(exception)}",
            details={"exception_type": type(exception).__name__}
        )


ENDPOINT_ERROR_MAPPING: Dict[str, Dict[str, ErrorCode]] = {
    "/run/error_device": {
        "NO_MIC": ErrorCode.DEVICE_NO_MIC,
        "NO_SPEAKER": ErrorCode.DEVICE_NO_SPEAKER,
    },
    "/run/error_translation_engine": {
        "LIMIT": ErrorCode.TRANSLATION_ENGINE_LIMIT,
    },
    "/set/data/mic_threshold": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_THRESHOLD,
    },
    "/set/data/speaker_threshold": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_THRESHOLD,
    },
    "/set/data/mic_record_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_RECORD_TIMEOUT,
    },
    "/set/data/mic_phrase_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_PHRASE_TIMEOUT,
    },
    "/set/data/mic_max_phrases": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_MIC_MAX_PHRASES,
    },
    "/set/data/speaker_record_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_RECORD_TIMEOUT,
    },
    "/set/data/speaker_phrase_timeout": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_PHRASE_TIMEOUT,
    },
    "/set/data/speaker_max_phrases": {
        "OUT_OF_RANGE": ErrorCode.VALIDATION_SPEAKER_MAX_PHRASES,
    },
    "/set/data/osc_ip_address": {
        "INVALID": ErrorCode.VALIDATION_INVALID_IP,
        "CANNOT_SET": ErrorCode.VALIDATION_CANNOT_SET_IP,
    },
    "/set/data/deepl_auth_key": {
        "LENGTH": ErrorCode.AUTH_DEEPL_LENGTH,
        "FAILED": ErrorCode.AUTH_DEEPL_FAILED,
    },
    "/set/data/gemini_auth_key": {
        "LENGTH": ErrorCode.AUTH_GEMINI_LENGTH,
        "FAILED": ErrorCode.AUTH_GEMINI_FAILED,
    },
    "/set/data/selected_gemini_model": {
        "INVALID": ErrorCode.MODEL_GEMINI_INVALID,
    },
    "/set/data/openai_auth_key": {
        "INVALID": ErrorCode.AUTH_OPENAI_INVALID,
        "FAILED": ErrorCode.AUTH_OPENAI_FAILED,
    },
    "/set/data/selected_openai_model": {
        "INVALID": ErrorCode.MODEL_OPENAI_INVALID,
    },
    "/set/data/siliconflow_auth_key": {
        "INVALID": ErrorCode.AUTH_SILICONFLOW_INVALID,
        "FAILED": ErrorCode.AUTH_SILICONFLOW_FAILED,
    },
    "/set/data/selected_siliconflow_model": {
        "INVALID": ErrorCode.MODEL_SILICONFLOW_INVALID,
    },
    "/set/data/websocket_host": {
        "INVALID_IP": ErrorCode.VALIDATION_INVALID_IP,
        "UNAVAILABLE": ErrorCode.WEBSOCKET_HOST_INVALID,
    },
    "/set/data/websocket_port": {
        "UNAVAILABLE": ErrorCode.WEBSOCKET_PORT_UNAVAILABLE,
    },
    "/set/enable/websocket_server": {
        "UNAVAILABLE": ErrorCode.WEBSOCKET_SERVER_UNAVAILABLE,
    },
    "/set/enable/vrc_mic_mute_sync": {
        "OSC_DISABLED": ErrorCode.VRC_MIC_MUTE_SYNC_OSC_DISABLED,
    },
}


def get_error_metadata(error_code: ErrorCode) -> Dict[str, Any]:
    return ERROR_METADATA.get(error_code, ERROR_METADATA[ErrorCode.GENERAL_UNKNOWN])


def is_critical_error(error_code: ErrorCode) -> bool:
    metadata = get_error_metadata(error_code)
    return metadata.get("severity") == "critical"


def requires_user_action(error_code: ErrorCode) -> bool:
    metadata = get_error_metadata(error_code)
    return metadata.get("user_action_required", False)
