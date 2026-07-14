from odoo import models, fields
from ..models.transcriber import AudioTranscriber
import base64

class AudioTranscriberWizard(models.TransientModel):
    _name = 'audio.transcriber.wizard'
    _description = 'Audio Transcriber Wizard'

    name = fields.Char('Title')
    audio_file = fields.Binary('Audio File')
    file_name = fields.Char()
    transcription = fields.Text('Transcription', readonly=True)

    def transcribe_audio(self):
        binary_data = base64.b64decode(self.audio_file)
        self.transcription = AudioTranscriber.transcribe_audio_convert(self,audio_binary_data=binary_data)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'audio.transcriber.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'views': [(self.env.ref('audio_file_to_text.view_audio_transcriber_wizard').id, "form")],
        }
    
    def action_add_chatter(self):
        user = self.env.user
        record_id = self._context['res_id']
        record_model = self._context['res_model']
        record = self.env[record_model].browse(record_id)

        attachment_values = {
            "name": self.file_name,
            "datas": self.audio_file,
            "res_model": record_model,
            "res_id": record.id,
            "res_name": record.name,
        }

        transcribe_values = {
            "body": self.transcription,
            "email_from": user.partner_id.email,
            "author_id": user.partner_id.id,
            "message_type": 'notification',
            "model": record_model,
            "record_name": record.name,
            "res_id": record.id,
            "attachment_ids": [(0,0,attachment_values)]
        }
        if transcribe_values and transcribe_values["attachment_ids"] and transcribe_values["body"]:
            self.env["mail.message"].create(transcribe_values)
            return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

