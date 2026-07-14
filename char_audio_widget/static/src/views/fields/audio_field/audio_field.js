/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useState, onWillUnmount, useEffect } from "@odoo/owl";
import { Field } from "@web/views/fields/field";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class AudioRecorderField extends Field {
    static template = "char_audio_widget.AudioRecorderField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.user = user;
        this.orm = useService("orm");
        this.state = useState({
            isRecording: false,
            duration: 0,
            inputValue: this.props.record.data[this.props.name] || "",
            isMounted: true, // Track mount state
        });

        this.recognition = null;
        this.timer = null;
        this.maxDuration = 30 * 60;
        this.startTimestamp = null;
        this.activePromises = new Set(); // Track active promises

        // Cleanup on unmount
        onWillUnmount(() => {
            this.state.isMounted = false;
            this.stopRecording();
            
            // Cancel all pending promises
            this.activePromises.forEach(promise => {
                if (promise.cancel) promise.cancel();
            });
            this.activePromises.clear();
        });

        // Handle component destruction during async operations
        useEffect(
            () => () => {
                this.state.isMounted = false;
                this.stopRecording();
            },
            () => []
        );
    }

    
    async startRecordingSecondary() {
        if (this.props.readonly) {
        return;
        }

        if (!this.state.isRecording) {
        this.state.isRecording = true;
        this.state.isProcessing = true;
        this.startTimer();

        try {
            const result = await this.orm.call(
            "audio.converter",
            "recognize_speech",
            []
            );

            if (result.error) {
            this.notification.add(result.error, {
                type: "danger",
                title: _t("Error"),
            });
            return;
            }
            const updatedText = this.state.inputValue 
                    ? `${this.state.inputValue} ${result.text}`
                    : result.text;
                
            const updatePromise = this.updateValue(updatedText);
            this.trackPromise(updatePromise);
            updatePromise.finally(() => this.untrackPromise(updatePromise));
        } catch (err) {
            console.error("Error converting audio to text:", err);
            this.notification.add(
            _t("Failed to process audio. Please try again."),
            {
                type: "danger",
                title: _t("Error"),
            }
            );
        } finally {
            this.state.isRecording = false;
            this.state.isProcessing = false;
            this.stopTimer();
        }
        }
    }

    async startRecording() {
        if (this.props.readonly || !this.state.isMounted) return;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let domain = [["id", "=", this.user.userId]]
        let userRecord = await this.orm.searchRead("res.users", domain, ["browser_config"], { limit: 1 });
        
        let Browser = userRecord[0].browser_config
        let recognitionTool = Boolean(SpeechRecognition)
        let isBrave = Boolean(window.navigator.brave && typeof window.navigator.brave.isBrave)

        if ((Browser === 'chrome' && recognitionTool === false) ||
            (Browser === 'chrome' && recognitionTool === isBrave) ||
            (Browser !== 'chrome' && recognitionTool === true && isBrave === false)
            ) {
            this.notification.add(_t("Browser not supported. Please check user configuration"), { type: "danger" });
            return
        }
        if (Browser != "chrome"){
            this.startRecordingSecondary();
            return
        }

        let voiceLang = "en-US";
        try {
            let langPromise = rpc("/web/dataset/call_kw", {
                model: "res.users",
                method: "get_voice_language",
                args: [[]],
                kwargs: {},
            });
            this.trackPromise(langPromise);
            voiceLang = await langPromise;
        } catch (error) {
            if (this.state.isMounted) {
                console.error("Failed to get voice language:", error);
            }
            return;
        }
        
        if (!this.state.isMounted) return;

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.lang = voiceLang;
        this.recognition.interimResults = false;

        this.startTimestamp = Date.now();
        this.state.isRecording = true;
        this.startTimer();

        this.recognition.onresult = (event) => {
            if (!this.state.isMounted) return;
            
            const transcript = event.results[event.results.length - 1][0].transcript;
            const updatedText = this.state.inputValue 
                ? `${this.state.inputValue} ${transcript}`
                : transcript;
            
            const updatePromise = this.updateValue(updatedText);
            this.trackPromise(updatePromise);
            updatePromise.finally(() => this.untrackPromise(updatePromise));
        };

        this.recognition.onend = () => {
            if (this.state.isMounted && this.state.isRecording) {
                this.recognition.start();
            }
        };

        this.recognition.start();
    }

    trackPromise(promise) {
        this.activePromises.add(promise);
    }

    untrackPromise(promise) {
        this.activePromises.delete(promise);
    }

    async updateValue(value) {
        if (!this.state.isMounted) return;

        this.state.inputValue = value;
        this.props.record.update({ [this.props.name]: value });
        
        try {
            const savePromise = this.props.record.save 
                ? this.props.record.save({
                    savePoint: true,
                    reload: false
                })
                : this.orm.write(
                    this.props.record.resModel,
                    [this.props.record.resId],
                    { [this.props.name]: value }
                );
            
            this.trackPromise(savePromise);
            await savePromise;
            
            if (this.state.isMounted && !this.props.record.save) {
                this.props.record.model.notify();
            }
        } catch (error) {
            if (this.state.isMounted) {
                console.error("Save failed:", error);
                this.notification.add(_t("Failed to save transcription"), { type: "danger" });
            }
        } 
    }

    async stopRecording() {
        if (!this.state.isMounted) return;

        if (this.recognition) {
            try {
                this.recognition.stop();
            } catch (e) {
                console.warn("Error stopping recognition:", e);
            }
            this.recognition = null;
        }
        
        this.state.isRecording = false;
        this.stopTimer();
        
        if (this.state.inputValue) {
            const finalSavePromise = this.updateValue(this.state.inputValue);
            this.trackPromise(finalSavePromise);
            await finalSavePromise;
            this.untrackPromise(finalSavePromise);
        }
    }

    startTimer() {
        if (!this.state.isMounted) return;

        this.state.duration = 0;
        this.timer = setInterval(() => {
            if (!this.state.isMounted) {
                this.stopTimer();
                return;
            }
            
            this.state.duration += 1;
            if (this.state.duration >= this.maxDuration) {
                this.stopRecording();
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    onInputChange(ev) {
        if (this.props.readonly || !this.state.isMounted) return;
        const updatePromise = this.updateValue(ev.target.value);
        this.trackPromise(updatePromise);
        updatePromise.finally(() => this.untrackPromise(updatePromise));
    }

    formatDuration(seconds) {
        const m = Math.floor(seconds / 60).toString().padStart(2, "0");
        const s = (seconds % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    }
}

export const audioRecorderField = {
    component: AudioRecorderField,
    displayName: "Audio Recorder",
    supportedTypes: ["char", "text"],
    extractProps: ({ attrs }) => ({
        readonly: attrs.readonly,
    }),
};

registry.category("fields").add("audio_recorder", audioRecorderField);