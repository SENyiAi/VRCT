import { useState, useRef, useCallback, useEffect } from "react";
import styles from "./Honkai.module.scss";
import { useLLMConnection } from "@logics_common";

const ENGINES = [
    { id: "SiliconFlow_API", label: "SiliconFlow", supports: { thinking: true, asr_correction: true } },
    { id: "Custom_OpenAI_API", label: "Custom OpenAI 1", supports: { thinking: false, asr_correction: true } },
    { id: "Custom_OpenAI_API_2", label: "Custom OpenAI 2", supports: { thinking: false, asr_correction: true } },
    { id: "Custom_OpenAI_API_3", label: "Custom OpenAI 3", supports: { thinking: false, asr_correction: true } },
];

const TranslationTestSection = () => {
    const { currentDevTestResult, testTranslationDetailed } = useLLMConnection();
    const [engine, setEngine] = useState("SiliconFlow_API");
    const [text, setText] = useState("");
    const [inputLang, setInputLang] = useState("Chinese (Simplified)");
    const [outputLang, setOutputLang] = useState("Japanese");
    const [enableThinking, setEnableThinking] = useState(true);
    const [enableAsrCorrection, setEnableAsrCorrection] = useState(false);

    const engineDef = ENGINES.find(e => e.id === engine) || ENGINES[0];
    const isPending = currentDevTestResult?.state === "pending";

    const handleTest = () => {
        if (!text.trim() || isPending) return;
        const options = {};
        if (engineDef.supports.thinking) options.enable_thinking = enableThinking;
        if (engineDef.supports.asr_correction) options.enable_asr_correction = enableAsrCorrection;
        testTranslationDetailed(engine, text, inputLang, outputLang, options);
    };

    const result = currentDevTestResult?.data;

    return (
        <div className={styles.section}>
            <div className={styles.section_title}>翻译引擎测试</div>

            <div className={styles.engine_selector}>
                {ENGINES.map(e => (
                    <button
                        key={e.id}
                        className={engine === e.id ? styles.engine_tab_active : styles.engine_tab}
                        onClick={() => setEngine(e.id)}
                    >
                        {e.label}
                    </button>
                ))}
            </div>

            <div className={styles.test_row}>
                <span className={styles.test_label}>语言</span>
                <input
                    className={styles.test_lang_input}
                    value={inputLang}
                    onChange={e => setInputLang(e.target.value)}
                    placeholder="源语言"
                />
                <span className={styles.test_arrow}>→</span>
                <input
                    className={styles.test_lang_input}
                    value={outputLang}
                    onChange={e => setOutputLang(e.target.value)}
                    placeholder="目标语言"
                />
            </div>

            <div className={styles.options_row}>
                <label className={`${styles.option_item} ${!engineDef.supports.thinking ? styles.option_disabled : ""}`}>
                    <input
                        type="checkbox"
                        className={styles.option_checkbox}
                        checked={enableThinking}
                        onChange={e => setEnableThinking(e.target.checked)}
                        disabled={!engineDef.supports.thinking}
                    />
                    <span className={styles.option_label}>启用思考</span>
                </label>
                <label className={`${styles.option_item} ${!engineDef.supports.asr_correction ? styles.option_disabled : ""}`}>
                    <input
                        type="checkbox"
                        className={styles.option_checkbox}
                        checked={enableAsrCorrection}
                        onChange={e => setEnableAsrCorrection(e.target.checked)}
                        disabled={!engineDef.supports.asr_correction}
                    />
                    <span className={styles.option_label}>启用ASR纠正</span>
                </label>
            </div>

            <div className={styles.test_row}>
                <input
                    className={styles.test_text_input}
                    value={text}
                    onChange={e => setText(e.target.value)}
                    placeholder="输入测试文本..."
                    onKeyDown={e => { if (e.key === "Enter") handleTest(); }}
                />
                <button
                    className={styles.test_button}
                    onClick={handleTest}
                    disabled={isPending || !text.trim()}
                >
                    测试
                </button>
            </div>

            {isPending && (
                <div className={styles.result_box}>
                    <span className={styles.result_pending}>请求中...</span>
                </div>
            )}

            {!isPending && result && (
                <div className={styles.result_box}>
                    {result.error ? (
                        <div className={styles.result_row}>
                            <span className={styles.result_key}>错误</span>
                            <span className={styles.result_error}>{result.error}</span>
                        </div>
                    ) : (
                        <>
                            <div className={styles.result_row}>
                                <span className={styles.result_key}>翻译结果</span>
                                <span className={styles.result_value}>{result.translated}</span>
                            </div>
                            {result.corrected_source && (
                                <div className={styles.result_row}>
                                    <span className={styles.result_key}>纠正后原文</span>
                                    <span className={styles.result_value}>{result.corrected_source}</span>
                                </div>
                            )}
                            <div className={styles.result_row}>
                                <span className={styles.result_key}>引擎</span>
                                <span className={styles.result_value}>{result.engine}</span>
                            </div>
                            <div className={styles.result_row}>
                                <span className={styles.result_key}>模型</span>
                                <span className={styles.result_value}>{result.model}</span>
                            </div>
                            {result.api_url && (
                                <div className={styles.result_row}>
                                    <span className={styles.result_key}>API URL</span>
                                    <span className={styles.result_value}>{result.api_url}</span>
                                </div>
                            )}
                            <div className={styles.result_row}>
                                <span className={styles.result_key}>耗时</span>
                                <span className={styles.result_value}>{result.elapsed_sec}s</span>
                            </div>
                            {result.options_used && Object.keys(result.options_used).length > 0 && (
                                <div className={styles.result_row}>
                                    <span className={styles.result_key}>使用选项</span>
                                    <span className={styles.result_value}>{JSON.stringify(result.options_used, null, 2)}</span>
                                </div>
                            )}
                            <div className={styles.result_row}>
                                <span className={styles.result_key}>输入</span>
                                <span className={styles.result_value}>{JSON.stringify(result.input, null, 2)}</span>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

const RESTART_DELAY_MS = 300;

const WebViewTestSection = () => {
    const [isRunning, setIsRunning] = useState(false);
    const [results, setResults] = useState([]);
    const [langCode, setLangCode] = useState("zh-CN");
    const recognitionRef = useRef(null);
    const shouldRunRef = useRef(false);
    const restartTimeoutRef = useRef(null);

    const stopRecognition = useCallback(() => {
        shouldRunRef.current = false;
        if (restartTimeoutRef.current) {
            clearTimeout(restartTimeoutRef.current);
            restartTimeoutRef.current = null;
        }
        if (recognitionRef.current) {
            try {
                recognitionRef.current.onresult = null;
                recognitionRef.current.onerror = null;
                recognitionRef.current.onend = null;
                recognitionRef.current.abort();
            } catch { /* empty */ }
            recognitionRef.current = null;
        }
        setIsRunning(false);
    }, []);

    const startRecognition = useCallback(() => {
        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
        if (!SpeechRecognition) {
            setResults(prev => [...prev, { type: "error", text: "Web Speech API 不可用" }]);
            return;
        }

        shouldRunRef.current = true;
        setIsRunning(true);

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = langCode;
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const r = event.results[i];
                if (r.isFinal) {
                    const text = r[0].transcript.trim();
                    if (text) {
                        setResults(prev => [...prev, { type: "final", text, confidence: r[0].confidence }]);
                    }
                }
            }
        };

        recognition.onerror = (event) => {
            setResults(prev => [...prev, { type: "error", text: `错误: ${event.error}` }]);
            if (event.error === "not-allowed" || event.error === "service-not-available") {
                shouldRunRef.current = false;
                setIsRunning(false);
            }
        };

        recognition.onend = () => {
            recognitionRef.current = null;
            if (shouldRunRef.current) {
                restartTimeoutRef.current = setTimeout(() => {
                    restartTimeoutRef.current = null;
                    if (shouldRunRef.current) {
                        startRecognition();
                    }
                }, RESTART_DELAY_MS);
            } else {
                setIsRunning(false);
            }
        };

        recognitionRef.current = recognition;
        try {
            recognition.start();
        } catch (e) {
            setResults(prev => [...prev, { type: "error", text: `启动失败: ${e.message}` }]);
            setIsRunning(false);
            recognitionRef.current = null;
        }
    }, [langCode]);

    useEffect(() => {
        return () => stopRecognition();
    }, [stopRecognition]);

    return (
        <div className={styles.section}>
            <div className={styles.section_title}>WebView 语音识别测试</div>

            <div className={styles.test_row}>
                <span className={styles.test_label}>BCP-47</span>
                <input
                    className={styles.test_lang_input}
                    value={langCode}
                    onChange={e => setLangCode(e.target.value)}
                    placeholder="zh-CN, en-US, ja-JP..."
                />
                <div className={styles.webview_status}>
                    <div className={`${styles.status_dot} ${isRunning ? styles.status_active : styles.status_inactive}`} />
                    <span className={styles.status_text}>{isRunning ? "识别中" : "未启动"}</span>
                </div>
            </div>

            <div className={styles.test_row}>
                <button
                    className={styles.test_button}
                    onClick={isRunning ? stopRecognition : startRecognition}
                >
                    {isRunning ? "停止" : "开始识别"}
                </button>
                <button
                    className={styles.test_button}
                    onClick={() => setResults([])}
                    style={{ backgroundColor: "transparent", border: "solid 0.1rem var(--dark_600_color)", color: "var(--dark_300_color)" }}
                >
                    清空
                </button>
            </div>

            {results.length > 0 && (
                <div className={styles.result_box}>
                    {results.map((r, i) => (
                        <div key={i} className={styles.result_row}>
                            <span className={styles.result_key}>
                                {r.type === "final" ? `[结果${r.confidence != null ? ` ${(r.confidence * 100).toFixed(0)}%` : ""}]` : "[错误]"}
                            </span>
                            <span className={r.type === "error" ? styles.result_error : styles.result_value}>
                                {r.text}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export const Honkai = () => {
    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <span className={styles.title}>Honkai</span>
                <span className={styles.subtitle}>开发者选项</span>
            </div>

            <TranslationTestSection />
            <WebViewTestSection />
        </div>
    );
};
