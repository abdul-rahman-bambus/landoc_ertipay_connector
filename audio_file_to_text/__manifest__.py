{
    "name": "Audio File to Text",
    "version": "18.0.1.0",
    "summary": "Audio File to Text" "",
    "author": "",
    "website": "",
    "license": "OPL-1",
    "category": "Extra Tools",
    "depends": ["web", "base", "sale", "sale_management", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/transcriber.xml",
        "views/res_trans_lang.xml",
        "views/res_users.xml",
        "views/transcribe.xml",
    ],
    "external_dependencies":{
        "python": ['FFmpeg', 'PyAudio', 'SpeechRecognition']
    },
    "assets": {
        "web.assets_backend": [
            "audio_file_to_text/static/src/chatter_transcriber/*",
        ],
    },
    "application": True,
    "auto_install": False,
}
