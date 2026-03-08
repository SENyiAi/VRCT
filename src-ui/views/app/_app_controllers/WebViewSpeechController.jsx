import { useEffect, useRef, useCallback } from "react";
import { useStdoutToPython } from "@useStdoutToPython";
import {
    useStore_TranscriptionSendStatus,
    useStore_IsBackendReady,
} from "@store";
import { useTranscription } from "@logics_configs";

export const WebViewSpeechController = () => {
    const recognitionRef = useRef(null);
    const isRunningRef = useRef(false);
    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentTranscriptionSendStatus } = useStore_TranscriptionSendStatus();
    const { currentIsBackendReady } = useStore_IsBackendReady();
    const { currentSelectedTranscriptionEngine } = useTranscription();

    const startRecognition = useCallback(() => {
        if (isRunningRef.current) return;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.error("[WebView Speech] Web Speech API is not available in this webview");
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        recognition.lang = "zh-CN";

        recognitionRef.current = recognition;
        isRunningRef.current = true;

        recognition.onresult = (event) => {
            if (event.results.length > 0) {
                const lastResult = event.results[event.results.length - 1];
                const transcript = lastResult[0].transcript.trim();
                const isFinal = lastResult.isFinal;

                if (isFinal && transcript.length > 0) {
                    console.log("[WebView Speech] Final:", transcript);
                    asyncStdoutToPython("/run/webview_transcription_result", {
                        text: transcript,
                        language: null,
                        is_final: true,
                    });
                }
            }
        };

        recognition.onend = () => {
            if (isRunningRef.current) {
                setTimeout(() => {
                    try {
                        recognitionRef.current?.start();
                    } catch (e) {
                        console.warn("[WebView Speech] Restart failed:", e);
                    }
                }, 300);
            }
        };

        recognition.onerror = (e) => {
            if (e.error !== "no-speech" && e.error !== "aborted") {
                console.error("[WebView Speech] Error:", e.error, e.message);
            }
            if (isRunningRef.current) {
                setTimeout(() => {
                    try {
                        recognitionRef.current?.start();
                    } catch (err) { /* empty */ }
                }, 500);
            }
        };

        recognition.onnomatch = () => {
            if (isRunningRef.current) {
                setTimeout(() => {
                    try {
                        recognitionRef.current?.start();
                    } catch (e) { /* empty */ }
                }, 500);
            }
        };

        try {
            recognition.start();
            console.log("[WebView Speech] Recognition started, lang=", recognition.lang);
        } catch (e) {
            console.error("[WebView Speech] Failed to start:", e);
            isRunningRef.current = false;
        }
    }, [asyncStdoutToPython]);

    const stopRecognition = useCallback(() => {
        isRunningRef.current = false;
        if (recognitionRef.current) {
            try {
                recognitionRef.current.stop();
            } catch (e) { /* empty */ }
            recognitionRef.current = null;
            console.log("[WebView Speech] Recognition stopped");
        }
    }, []);

    useEffect(() => {
        if (!currentIsBackendReady?.data) return;

        const isWebView = currentSelectedTranscriptionEngine?.data === "WebView";
        const isSendEnabled = currentTranscriptionSendStatus?.data === true;

        if (isWebView && isSendEnabled) {
            startRecognition();
        } else {
            stopRecognition();
        }

        return () => {
            stopRecognition();
        };
    }, [currentSelectedTranscriptionEngine?.data, currentTranscriptionSendStatus?.data, currentIsBackendReady?.data, startRecognition, stopRecognition]);

    return null;
};
