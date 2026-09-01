{
    'name': 'Payment Provider: Ertipay',
    'version': '18.0.1.3.1',
    'category': 'Accounting/Payment Providers',
    'summary': 'Accept UPI payments through the Ertipay pay-in gateway.',
    'description': """
        Integrates the Ertipay UPI pay-in gateway with Odoo Payment. It supports
        full and partial payable amounts, gateway charges, API authentication,
        encrypted request and response payloads, payment creation, redirects,
        callbacks, status checks, UAT simulation, and invoice payment metadata.
    """,
    'author': 'Bambus Technologies LLP',
    'website': 'https://bambustechnologies.in/',
    'depends': ['payment', 'website_payment', 'account'],
    'data': [
        'views/payment_ertipay_templates.xml',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/account_move_views.xml',
        'data/payment_provider_data.xml',
        'data/payment_method_data.xml',
    ],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
