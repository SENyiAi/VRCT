import { useStdoutToPython } from "@useStdoutToPython";
import {
    useStore_IsLMStudioConnected,
    useStore_IsOllamaConnected,
    useStore_IsCustomOpenAIConnected,
    useStore_CustomOpenAITestResult,
    useStore_IsCustomOpenAI2Connected,
    useStore_CustomOpenAI2TestResult,
    useStore_IsCustomOpenAI3Connected,
    useStore_CustomOpenAI3TestResult,
    useStore_DevTestResult,
} from "@store";

export const useLLMConnection = () => {
    const { asyncStdoutToPython } = useStdoutToPython();
    const {
        currentIsLMStudioConnected,
        updateIsLMStudioConnected,
        pendingIsLMStudioConnected,
    } = useStore_IsLMStudioConnected();
    const {
        currentIsOllamaConnected,
        updateIsOllamaConnected,
        pendingIsOllamaConnected,
    } = useStore_IsOllamaConnected();
    const {
        currentIsCustomOpenAIConnected,
        updateIsCustomOpenAIConnected,
        pendingIsCustomOpenAIConnected,
    } = useStore_IsCustomOpenAIConnected();
    const {
        currentCustomOpenAITestResult,
        updateCustomOpenAITestResult,
        pendingCustomOpenAITestResult,
    } = useStore_CustomOpenAITestResult();
    const {
        currentIsCustomOpenAI2Connected,
        updateIsCustomOpenAI2Connected,
        pendingIsCustomOpenAI2Connected,
    } = useStore_IsCustomOpenAI2Connected();
    const {
        currentCustomOpenAI2TestResult,
        updateCustomOpenAI2TestResult,
        pendingCustomOpenAI2TestResult,
    } = useStore_CustomOpenAI2TestResult();
    const {
        currentIsCustomOpenAI3Connected,
        updateIsCustomOpenAI3Connected,
        pendingIsCustomOpenAI3Connected,
    } = useStore_IsCustomOpenAI3Connected();
    const {
        currentCustomOpenAI3TestResult,
        updateCustomOpenAI3TestResult,
        pendingCustomOpenAI3TestResult,
    } = useStore_CustomOpenAI3TestResult();

    const {
        currentDevTestResult,
        updateDevTestResult,
        pendingDevTestResult,
    } = useStore_DevTestResult();

    const checkConnection_LMStudio = () => {
        pendingIsLMStudioConnected();
        asyncStdoutToPython("/run/lmstudio_connection");
    };
    const setConnectionStatus_LMStudio = (is_connected) => {
        updateIsLMStudioConnected(is_connected);
    };

    const checkConnection_Ollama = () => {
        pendingIsOllamaConnected();
        asyncStdoutToPython("/run/ollama_connection");
    };
    const setConnectionStatus_Ollama = (is_connected) => {
        updateIsOllamaConnected(is_connected);
    };

    const checkConnection_CustomOpenAI = () => {
        pendingIsCustomOpenAIConnected();
        asyncStdoutToPython("/run/custom_openai_connection");
    };
    const setConnectionStatus_CustomOpenAI = (is_connected) => {
        updateIsCustomOpenAIConnected(is_connected);
    };

    const testTranslation_CustomOpenAI = (text, input_lang, output_lang) => {
        pendingCustomOpenAITestResult();
        asyncStdoutToPython("/run/test_custom_openai_translation", { text, input_lang, output_lang });
    };
    const setTestTranslationResult_CustomOpenAI = (result) => {
        updateCustomOpenAITestResult(result);
    };

    const checkConnection_CustomOpenAI2 = () => {
        pendingIsCustomOpenAI2Connected();
        asyncStdoutToPython("/run/custom_openai_2_connection");
    };
    const setConnectionStatus_CustomOpenAI2 = (is_connected) => {
        updateIsCustomOpenAI2Connected(is_connected);
    };

    const testTranslation_CustomOpenAI2 = (text, input_lang, output_lang) => {
        pendingCustomOpenAI2TestResult();
        asyncStdoutToPython("/run/test_custom_openai_2_translation", { text, input_lang, output_lang });
    };
    const setTestTranslationResult_CustomOpenAI2 = (result) => {
        updateCustomOpenAI2TestResult(result);
    };

    const checkConnection_CustomOpenAI3 = () => {
        pendingIsCustomOpenAI3Connected();
        asyncStdoutToPython("/run/custom_openai_3_connection");
    };
    const setConnectionStatus_CustomOpenAI3 = (is_connected) => {
        updateIsCustomOpenAI3Connected(is_connected);
    };

    const testTranslation_CustomOpenAI3 = (text, input_lang, output_lang) => {
        pendingCustomOpenAI3TestResult();
        asyncStdoutToPython("/run/test_custom_openai_3_translation", { text, input_lang, output_lang });
    };
    const setTestTranslationResult_CustomOpenAI3 = (result) => {
        updateCustomOpenAI3TestResult(result);
    };

    const testTranslationDetailed = (engine, text, input_lang, output_lang, options = {}) => {
        pendingDevTestResult();
        asyncStdoutToPython("/run/test_translation_engine_detailed", { engine, text, input_lang, output_lang, options });
    };
    const setDetailedTestResult = (result) => {
        updateDevTestResult(result);
    };

    return {
        currentIsLMStudioConnected,
        updateIsLMStudioConnected,
        setConnectionStatus_LMStudio,
        checkConnection_LMStudio,

        currentIsOllamaConnected,
        updateIsOllamaConnected,
        setConnectionStatus_Ollama,
        checkConnection_Ollama,

        currentIsCustomOpenAIConnected,
        updateIsCustomOpenAIConnected,
        setConnectionStatus_CustomOpenAI,
        checkConnection_CustomOpenAI,

        currentCustomOpenAITestResult,
        testTranslation_CustomOpenAI,
        setTestTranslationResult_CustomOpenAI,

        currentIsCustomOpenAI2Connected,
        updateIsCustomOpenAI2Connected,
        setConnectionStatus_CustomOpenAI2,
        checkConnection_CustomOpenAI2,

        currentCustomOpenAI2TestResult,
        testTranslation_CustomOpenAI2,
        setTestTranslationResult_CustomOpenAI2,

        currentIsCustomOpenAI3Connected,
        updateIsCustomOpenAI3Connected,
        setConnectionStatus_CustomOpenAI3,
        checkConnection_CustomOpenAI3,

        currentCustomOpenAI3TestResult,
        testTranslation_CustomOpenAI3,
        setTestTranslationResult_CustomOpenAI3,

        currentDevTestResult,
        testTranslationDetailed,
        setDetailedTestResult,
    };
};