{
    'name': 'Landoc N8N Connector',
    'version': '18.0',
    'category': 'Service',
    'active': True,
    'summary': 'N8N Connector',
    'author': 'Bambus Technologies LLP',
    'sequence': '1',
    'website': 'https://bambustechnologies.in/',
    'depends': [
        'base', 'sale', 'crm', 'custom_crm', 'contacts', 'partner_city_m2o', 'custom_landoc', 'sales_team', 'payment',
    ],
    'data': [
        'data/webhook_token.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': True,
}
