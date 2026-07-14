from odoo import models, fields
from pydub import AudioSegment

import base64
import tempfile
import os
import logging

_logger = logging.getLogger(__name__)

class AudioTranscriber(models.Model):
    _name = 'audio.transcriber'
    _description = 'Audio to Text Transcriber'

    name = fields.Char('Title')
    audio_file = fields.Binary('Audio File', required=True)
    file_name = fields.Char()
    transcription = fields.Text('Transcription', readonly=True)

    def transcribe_audio_convert(self, audio_binary_data):
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        
        try:
            # Save binary data to a temp file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_input:
                tmp_input.write(audio_binary_data)
                input_path = tmp_input.name
            
            # Convert to WAV (16-bit PCM, 16kHz) using pydub
            sound = AudioSegment.from_file(input_path)
            sound = sound.set_frame_rate(16000).set_channels(1)
            
            # Export to WAV format
            wav_path = input_path + ".wav"
            sound.export(wav_path, format="wav", codec="pcm_s16le")
            
            # Transcribe the WAV file
            with sr.AudioFile(wav_path) as source:
                language = self.env.user.voice_to_text_lang_id.code
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=language)
                return text
                
        except Exception as e:
            _logger.error(f"Transcription failed: {str(e)}")
            return False
        finally:
            # Clean up temp files
            if 'input_path' in locals() and os.path.exists(input_path):
                os.unlink(input_path)
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.unlink(wav_path)
                
    def transcribe_audio(self):
        audio = self.audio_file
        binary_data = base64.b64decode(audio)
        self.transcription = self.transcribe_audio_convert(binary_data)
