{
    'name': 'Currency Denomination',
    'version': '18.0',
    'category': 'Accounts',
    'active': True,
    'summary': 'Currency Denomination',
    'author': 'Bambus Technologies LLP',
    'sequence': '1',
    'website': 'https://bambustechnologies.in/',
    'depends': [
        'base', 'account', 'custom_landoc',
    ],
    'data': [
        # ---------- security ----------------#
        # 'security/security_currency.xml',
        'security/ir.model.access.csv',
        # ---------- views ----------------#
        'views/currency_denomination.xml',
    ],
    'description': """
    """,
    'demo_xml': [],
    'license': 'OPL-1',
    "images": ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
