import { useEffect, useRef, useCallback } from "react";
import { useStdoutToPython } from "@useStdoutToPython";
import {
    useStore_TranscriptionSendStatus,
    useStore_IsBackendReady,
} from "@store";
import { useTranscription } from "@logics_configs";

// Downsample Float32 PCM from source rate to target rate (linear interpolation)
function downsampleBuffer(buffer, fromRate, toRate) {
    if (fromRate === toRate) return buffer;
    const ratio = fromRate / toRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    for (let i = 0; i < newLength; i++) {
        const srcIdx = i * ratio;
        const idx = Math.floor(srcIdx);
        const frac = srcIdx - idx;
        result[i] = idx + 1 < buffer.length
            ? buffer[idx] * (1 - frac) + buffer[idx + 1] * frac
            : buffer[idx];
    }
    return result;
}

// Convert Float32 PCM [-1,1] to Int16 PCM bytes, then base64 encode
function pcmFloat32ToBase64(float32Data) {
    const int16 = new Int16Array(float32Data.length);
    for (let i = 0; i < float32Data.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Data[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    const bytes = new Uint8Array(int16.buffer);
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + chunk, bytes.length)));
    }
    return btoa(binary);
}

const TARGET_SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;
const SPEECH_THRESHOLD = 0.01;
const MIN_SPEECH_FRAMES = 2;
const MAX_SPEECH_SECONDS = 15;
const SILENCE_SECONDS = 1.2;

export const WebViewSpeechController = () => {
    const streamRef = useRef(null);
    const contextRef = useRef(null);
    const processorRef = useRef(null);
    const sourceRef = useRef(null);
    const isRunningRef = useRef(false);

    const speechBufferRef = useRef([]);
    const silenceCountRef = useRef(0);
    const speechFrameCountRef = useRef(0);
    const isSpeakingRef = useRef(false);

    const sendFnRef = useRef(null);

    const { asyncStdoutToPython } = useStdoutToPython();
    const { currentTranscriptionSendStatus } = useStore_TranscriptionSendStatus();
    const { currentIsBackendReady } = useStore_IsBackendReady();
    const { currentSelectedTranscriptionEngine } = useTranscription();

    // Keep send function ref current to avoid stale closures in onaudioprocess
    useEffect(() => {
        sendFnRef.current = asyncStdoutToPython;
    }, [asyncStdoutToPython]);

    const flushAndSend = useCallback((sampleRate) => {
        const buffers = speechBufferRef.current;
        speechBufferRef.current = [];
        silenceCountRef.current = 0;
        speechFrameCountRef.current = 0;
        isSpeakingRef.current = false;

        if (buffers.length < MIN_SPEECH_FRAMES) return;

        const totalLength = buffers.reduce((acc, b) => acc + b.length, 0);
        const combined = new Float32Array(totalLength);
        let offset = 0;
        for (const buf of buffers) {
            combined.set(buf, offset);
            offset += buf.length;
        }

        const resampled = downsampleBuffer(combined, sampleRate, TARGET_SAMPLE_RATE);
        const base64 = pcmFloat32ToBase64(resampled);
        const durationSec = (resampled.length / TARGET_SAMPLE_RATE).toFixed(1);

        console.log(`[WebView Audio] Sending ${durationSec}s audio (${(base64.length / 1024).toFixed(0)}KB)`);

        sendFnRef.current?.("/run/webview_audio_chunk", {
            audio_base64: base64,
            sample_rate: TARGET_SAMPLE_RATE,
            sample_width: 2,
        });
    }, []);

    const startCapture = useCallback(async () => {
        if (isRunningRef.current) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            });

            streamRef.current = stream;
            const context = new AudioContext();
            contextRef.current = context;

            // AudioContext may be suspended until user gesture; resume just in case
            if (context.state === "suspended") {
                await context.resume();
            }

            const actualRate = context.sampleRate;
            const framesPerSec = actualRate / BUFFER_SIZE;
            const silenceFrames = Math.max(3, Math.round(SILENCE_SECONDS * framesPerSec));
            const maxFrames = Math.round(MAX_SPEECH_SECONDS * framesPerSec);

            const source = context.createMediaStreamSource(stream);
            sourceRef.current = source;
            const processor = context.createScriptProcessor(BUFFER_SIZE, 1, 1);
            processorRef.current = processor;

            speechBufferRef.current = [];
            silenceCountRef.current = 0;
            speechFrameCountRef.current = 0;
            isSpeakingRef.current = false;
            isRunningRef.current = true;

            processor.onaudioprocess = (e) => {
                if (!isRunningRef.current) return;

                const pcm = e.inputBuffer.getChannelData(0);

                let sum = 0;
                for (let i = 0; i < pcm.length; i++) {
                    sum += pcm[i] * pcm[i];
                }
                const rms = Math.sqrt(sum / pcm.length);

                if (rms > SPEECH_THRESHOLD) {
                    silenceCountRef.current = 0;
                    speechFrameCountRef.current++;
                    speechBufferRef.current.push(new Float32Array(pcm));

                    if (speechFrameCountRef.current >= MIN_SPEECH_FRAMES) {
                        isSpeakingRef.current = true;
                    }
                } else {
                    silenceCountRef.current++;

                    if (isSpeakingRef.current) {
                        // Keep buffering a bit of trailing silence
                        speechBufferRef.current.push(new Float32Array(pcm));

                        if (silenceCountRef.current >= silenceFrames) {
                            flushAndSend(actualRate);
                        }
                    } else {
                        // No established speech — discard noise
                        if (silenceCountRef.current > silenceFrames) {
                            speechBufferRef.current = [];
                            speechFrameCountRef.current = 0;
                        }
                    }
                }

                // Force flush if max duration reached
                if (speechBufferRef.current.length >= maxFrames) {
                    flushAndSend(actualRate);
                }
            };

            source.connect(processor);
            processor.connect(context.destination);

            console.log("[WebView Audio] Capture started, sampleRate=", actualRate, "silenceFrames=", silenceFrames);
        } catch (e) {
            console.error("[WebView Audio] Failed to start capture:", e);
            isRunningRef.current = false;
        }
    }, [flushAndSend]);

    const stopCapture = useCallback(() => {
        isRunningRef.current = false;

        if (processorRef.current) {
            try { processorRef.current.disconnect(); } catch { /* empty */ }
            processorRef.current = null;
        }
        if (sourceRef.current) {
            try { sourceRef.current.disconnect(); } catch { /* empty */ }
            sourceRef.current = null;
        }
        if (contextRef.current) {
            try { contextRef.current.close(); } catch { /* empty */ }
            contextRef.current = null;
        }
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(t => t.stop());
            streamRef.current = null;
        }

        speechBufferRef.current = [];
        console.log("[WebView Audio] Capture stopped");
    }, []);

    useEffect(() => {
        if (!currentIsBackendReady?.data) return;

        const isWebView = currentSelectedTranscriptionEngine?.data === "WebView";
        const isSendEnabled = currentTranscriptionSendStatus?.data === true;

        if (isWebView && isSendEnabled) {
            startCapture();
        } else {
            stopCapture();
        }

        return () => {
            stopCapture();
        };
    }, [currentSelectedTranscriptionEngine?.data, currentTranscriptionSendStatus?.data, currentIsBackendReady?.data, startCapture, stopCapture]);

    return null;
};
