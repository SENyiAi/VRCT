import { useEffect, useRef, useCallback } from "react";
import { useStdoutToPython } from "@useStdoutToPython";
import {
    useStore_TranscriptionSendStatus,
    useStore_IsBackendReady,
    useStore_SelectedYourLanguages,
    useStore_SelectedPresetTabNumber,
} from "@store";
import { useTranscription } from "@logics_configs";

/**
 * WebView Speech Recognition Controller
 *
 * Uses the browser's native webkitSpeechRecognition (Web Speech API) to
 * perform speech-to-text directly in the Tauri WebView2 runtime — no Python
 * audio processing or network round-trip required.
 *
 * Architecture follows Kikitan Translator's proven pattern:
 * - Create a webkitSpeechRecognition instance
 * - Set continuous=true, interimResults=true
 * - Auto-restart on end/error with a short delay
 * - Send final transcription results directly to the Python backend
 */

const RESTART_DELAY_MS = 300;

export const WebViewSpeechController = () => {
    const recognitionRef = useRef(null);
    const isRunningRef = useRef(false);
    const shouldRunRef = useRef(false);
    const restartTimeoutRef = useRef(null);
    const sendFnRef = useRef(null);
    const langCodeRef = useRef("en-US");

    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentTranscriptionSendStatus } = useStore_TranscriptionSendStatus();
    const { currentIsBackendReady } = useStore_IsBackendReady();
    const { currentSelectedTranscriptionEngine } = useTranscription();
    const { currentSelectedYourLanguages } = useStore_SelectedYourLanguages();
    const { currentSelectedPresetTabNumber } = useStore_SelectedPresetTabNumber();

    // Keep send function ref current
    useEffect(() => {
        sendFnRef.current = asyncStdoutToPython;
    }, [asyncStdoutToPython]);

    // Derive BCP-47 language code from the selected language data
    useEffect(() => {
        try {
            const tabNo = currentSelectedPresetTabNumber?.data;
            const tabLangs = currentSelectedYourLanguages?.data?.[tabNo];
            if (!tabLangs) return;
            const firstEnabled = Object.values(tabLangs).find(v => v?.enable);
            if (firstEnabled?.webview_code) {
                langCodeRef.current = firstEnabled.webview_code;
                console.log("[WebView Speech] Language code updated:", langCodeRef.current);
            }
        } catch {
            // Keep previous langCode on error
        }
    }, [currentSelectedYourLanguages?.data, currentSelectedPresetTabNumber?.data]);

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
        isRunningRef.current = false;
        console.log("[WebView Speech] Stopped");
    }, []);

    const startRecognition = useCallback(() => {
        if (isRunningRef.current) return;

        const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
        if (!SpeechRecognition) {
            console.error("[WebView Speech] Web Speech API not available");
            return;
        }

        shouldRunRef.current = true;

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = langCodeRef.current;
        recognition.maxAlternatives = 1;

        recognition.onresult = (event) => {
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    const text = result[0].transcript.trim();
                    if (text) {
                        console.log("[WebView Speech] Final:", text);
                        sendFnRef.current?.("/run/webview_transcription_result", {
                            text: text,
                            language: null,
                            is_final: true,
                        });
                    }
                }
            }
        };

        recognition.onerror = (event) => {
            console.warn("[WebView Speech] Error:", event.error);
            // "no-speech" and "aborted" are recoverable
            if (event.error === "not-allowed" || event.error === "service-not-available") {
                console.error("[WebView Speech] Fatal error:", event.error);
                shouldRunRef.current = false;
            }
        };

        recognition.onend = () => {
            isRunningRef.current = false;
            recognitionRef.current = null;
            // Auto-restart if still supposed to run (Kikitan pattern)
            if (shouldRunRef.current) {
                restartTimeoutRef.current = setTimeout(() => {
                    restartTimeoutRef.current = null;
                    if (shouldRunRef.current) {
                        startRecognition();
                    }
                }, RESTART_DELAY_MS);
            }
        };

        recognitionRef.current = recognition;
        isRunningRef.current = true;

        try {
            recognition.start();
            console.log("[WebView Speech] Started, lang=", recognition.lang);
        } catch (e) {
            console.error("[WebView Speech] Failed to start:", e);
            isRunningRef.current = false;
            recognitionRef.current = null;
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

    // Update recognition language on the fly when language config changes
    useEffect(() => {
        if (recognitionRef.current && isRunningRef.current) {
            // Restart with the new language
            const prevShouldRun = shouldRunRef.current;
            stopRecognition();
            if (prevShouldRun) {
                setTimeout(() => startRecognition(), RESTART_DELAY_MS);
            }
        }
    }, [langCodeRef.current]);

    return null;
};
