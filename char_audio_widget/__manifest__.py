{
    "name": "Char Audio Recorder",
    "version": "18.0.1.0.0",
    "summary": "Char Audio Recorder",
    "author": "Mohammed Shahil, Bambus Technologies LLP",
    "website": "",
    "license": "OPL-1",
    "category": "Extra Tools",
    "depends": ["web", "base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_users.xml",
        "views/res_trans_lang.xml",
    ],
    # Commented because of py warnings.
    # "external_dependencies":{
    #     "python": ['FFmpeg', 'PyAudio', 'SpeechRecognition']
    # },
    "assets": {
        "web.assets_backend": [
            "char_audio_widget/static/src/views/fields/audio_field/audio_field.js",
            "char_audio_widget/static/src/views/fields/audio_field/audio_field.xml",
        ],
    },
    "application": True,
    "auto_install": False,
}
