from functools import lru_cache

import streamlit as st


VOICE_ASSISTANT_HTML = """
<div class="voice-assistant-root">
  <button class="voice-orb" type="button" aria-label="Voice assistant microphone">
    <span class="voice-orb-icon">🎙️</span>
  </button>
  <div class="voice-status">Prêt</div>
  <div class="voice-hint">Touchez l'orbe pour parler, puis touchez à nouveau pour envoyer.</div>
</div>
"""


VOICE_ASSISTANT_CSS = """
.voice-assistant-root {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  padding: 0.35rem 0 0.8rem 0;
}

.voice-orb {
  width: 170px;
  height: 170px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.18) 28%, transparent 29%),
    linear-gradient(145deg, #1f2937 0%, #111827 58%, #020617 100%);
  color: white;
  box-shadow:
    0 0 0 18px rgba(15, 23, 42, 0.06),
    0 24px 60px rgba(15, 23, 42, 0.28);
  transition: transform 180ms ease, box-shadow 180ms ease, filter 180ms ease;
}

.voice-orb:hover {
  transform: scale(1.02);
  filter: brightness(1.03);
}

.voice-orb:active {
  transform: scale(0.98);
}

.voice-orb.listening {
  animation: voice-pulse 1.3s infinite ease-in-out;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.18) 28%, transparent 29%),
    linear-gradient(145deg, #2563eb 0%, #1d4ed8 55%, #0f172a 100%);
  box-shadow:
    0 0 0 18px rgba(37, 99, 235, 0.12),
    0 24px 60px rgba(37, 99, 235, 0.26);
}

.voice-orb.processing,
.voice-orb.speaking {
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.18) 28%, transparent 29%),
    linear-gradient(145deg, #38bdf8 0%, #2563eb 52%, #0f172a 100%);
}

.voice-orb-icon {
  font-size: 3.25rem;
  line-height: 1;
}

.voice-status {
  color: #0f172a;
  font-size: 1.08rem;
  font-weight: 800;
  text-align: center;
}

.voice-hint {
  color: #64748b;
  font-size: 0.93rem;
  text-align: center;
  line-height: 1.45;
  max-width: 20rem;
}

@keyframes voice-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.03); }
  100% { transform: scale(1); }
}
"""


VOICE_ASSISTANT_JS = """
export default function(component) {
    const { parentElement, data, setTriggerValue } = component;
    const orb = parentElement.querySelector('.voice-orb');
    const status = parentElement.querySelector('.voice-status');
    const hint = parentElement.querySelector('.voice-hint');

    if (!orb || !status || !hint) return;

    let mediaRecorder = component.__mediaRecorder || null;
    let mediaStream = component.__mediaStream || null;
    let chunks = component.__chunks || [];
    let currentAudio = component.__currentAudio || null;
    let isBusy = component.__isBusy || false;
    let lastRequestNonce = component.__lastRequestNonce || null;
    let lastHandledResponseNonce = component.__lastHandledResponseNonce || null;


    // =========================
    // UI STATE
    // =========================
    const resetVisualState = () => {
        orb.classList.remove('listening', 'processing', 'speaking');
        status.textContent = 'Prêt';
        hint.textContent = "Touchez l'orbe pour parler, puis touchez à nouveau pour envoyer.";
    };

    const setVisualState = (mode, label, hintText) => {
        orb.classList.remove('listening', 'processing', 'speaking');
        if (mode) orb.classList.add(mode);
        status.textContent = label;
        hint.textContent = hintText;
    };

    // =========================
    // UTILS
    // =========================
    const blobToBase64 = (blob) =>
        new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const result = String(reader.result || '');
                resolve(result.includes(',') ? result.split(',')[1] : '');
            };
            reader.onerror = () => reject(reader.error);
            reader.readAsDataURL(blob);
        });

    const stopTracks = () => {
        if (mediaStream) {
            mediaStream.getTracks().forEach((t) => t.stop());
            mediaStream = null;
            component.__mediaStream = null;
        }
    };

    // =========================
    // 🔥 SEND TO STREAMLIT (NO FETCH)
    // =========================
    const sendRecording = async (blob, mimeType) => {
        const audioBase64 = await blobToBase64(blob);
        const nonce = Date.now();

        lastRequestNonce = nonce;
        component.__lastRequestNonce = nonce;

        isBusy = true;
        component.__isBusy = true;

        setVisualState('processing', 'Traitement...', 'Le robot prépare sa réponse.');

        setTriggerValue('voice_input', {
            nonce,
            audio_base64: audioBase64,
            mime_type: mimeType,
            conversation_id: data.conversation_id,
        });
    };

    // =========================
    // 🎤 RECORDING
    // =========================
    const startRecording = async () => {
        try {
            if (!navigator.mediaDevices?.getUserMedia) {
                throw new Error('Microphone not supported.');
            }

            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            component.__mediaStream = mediaStream;

            let mimeType = '';
            if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                mimeType = 'audio/webm;codecs=opus';
            } else if (MediaRecorder.isTypeSupported('audio/webm')) {
                mimeType = 'audio/webm';
            }

            mediaRecorder = mimeType
                ? new MediaRecorder(mediaStream, { mimeType })
                : new MediaRecorder(mediaStream);

            component.__mediaRecorder = mediaRecorder;

            chunks = [];
            component.__chunks = chunks;

            mediaRecorder.ondataavailable = (e) => {
                if (e.data?.size > 0) chunks.push(e.data);
            };

            mediaRecorder.onstop = async () => {
                try {
                    const actualMime = mediaRecorder.mimeType || 'audio/webm';
                    const blob = new Blob(chunks, { type: actualMime });
                    stopTracks();
                    await sendRecording(blob, actualMime);
                } catch (err) {
                    isBusy = false;
                    component.__isBusy = false;
                    setVisualState('', 'Erreur capture', 'Veuillez réessayer.');
                    setTriggerValue('error', String(err));
                }
            };

            mediaRecorder.start();
            setVisualState('listening', 'J’écoute...', "Touchez encore l'orbe quand terminé.");
        } catch (err) {
            setVisualState('', 'Micro bloqué', 'Autorisez le micro.');
            setTriggerValue('error', String(err));
        }
    };

    const stopRecording = async () => {
        if (mediaRecorder?.state === 'recording') {
            mediaRecorder.stop();
        }
    };

    // =========================
    // 🧠 HANDLE RESPONSE FROM PYTHON
    // =========================
    if (data.response && data.response.nonce !== lastHandledResponseNonce) {
        lastHandledResponseNonce = data.response.nonce;
        component.__lastHandledResponseNonce = lastHandledResponseNonce;

        const payload = data.response;

        // Pause previous audio if any (safe here — this is intentional)
        if (currentAudio) {
            currentAudio.onended = null;
            currentAudio.onerror = null;
            currentAudio.pause();
        }

        if (!payload.response_audio_base64) {
            isBusy = false;
            component.__isBusy = false;
            currentAudio = null;
            component.__currentAudio = null;
            setVisualState('', 'Réponse prête', 'Sans audio.');
        } else {
            currentAudio = new Audio(
                `data:${payload.response_audio_mime_type || 'audio/mpeg'};base64,${payload.response_audio_base64}`
            );
            component.__currentAudio = currentAudio;
            setVisualState('speaking', 'Réponse vocale', 'Le robot parle...');

            const playPromise = currentAudio.play();

            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        // Playing successfully — attach end/error handlers now
                        currentAudio.onended = () => {
                            isBusy = false;
                            component.__isBusy = false;
                            resetVisualState();
                            setTriggerValue('playback_finished', payload.nonce);
                        };
                        currentAudio.onerror = () => {
                            isBusy = false;
                            component.__isBusy = false;
                            setVisualState('', 'Erreur audio', 'Lecture échouée.');
                            setTriggerValue('error', 'Audio playback failed');
                        };
                    })
                    .catch((err) => {
                        if (err.name === 'AbortError') return; // Intentional teardown, ignore
                        console.error('AUDIO_PLAY_FAILED', err.name, err.message);
                        isBusy = false;
                        component.__isBusy = false;
                        setVisualState('', `Erreur: ${err.name}`, err.message || 'Lecture échouée.');
                        setTriggerValue('error', `${err.name}: ${err.message}`);
                    });
            }
        }
    }


    // =========================
    // CLICK
    // =========================
    orb.onclick = async () => {
        if (isBusy) return;

        if (mediaRecorder?.state === 'recording') {
            await stopRecording();
        } else {
            await startRecording();
        }
    };

    // =========================
    // RESET
    // =========================
    if (data.reset_token && data.reset_token !== component.__resetToken) {
        component.__resetToken = data.reset_token;

        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
            component.__currentAudio = null;
        }

        isBusy = false;
        component.__isBusy = false;

        resetVisualState();
    }

    if (!isBusy && !(mediaRecorder?.state === 'recording')) {
        resetVisualState();
    }

    
    // =========================
    // TEARDOWN — mic tracks only, never touch audio
    // =========================
    return () => {
        stopTracks(); // Clean up mic — this is fine on re-render
        // ✅ Do NOT pause currentAudio here — it must survive re-renders
    };
}
"""


@lru_cache(maxsize=1)
def _get_voice_component():
    return st.components.v2.component(
        "voice_assistant_orb",
        html=VOICE_ASSISTANT_HTML,
        css=VOICE_ASSISTANT_CSS,
        js=VOICE_ASSISTANT_JS,
    )


def voice_assistant_orb(*, key: str, data: dict | None = None):
    component = _get_voice_component()
    return component(
        key=key,
        data=data or {},
        default={
            "voice_result": None,
            "playback_finished": None,
            "error": None,
        },
        height="content",
        on_voice_result_change=lambda: None,
        on_playback_finished_change=lambda: None,
        on_error_change=lambda: None,
    )
