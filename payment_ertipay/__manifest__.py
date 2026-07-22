{
    'name': 'Payment Provider: Ertipay',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Payment Providers',
    'summary': 'Accept UPI payments through the Ertipay pay-in gateway.',
    'author': 'Bambus Technologies LLP',
    'website': 'https://bambustechnologies.in/',
    'depends': ['payment', 'website_payment'],
    'data': [
        'views/payment_ertipay_templates.xml',
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
