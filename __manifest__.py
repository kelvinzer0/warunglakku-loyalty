# -*- coding: utf-8 -*-
{
    'name': 'Warung Lakku Loyalty & Affiliate',
    'version': '17.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Point-to-voucher exchange + simple share-to-sosmed affiliate system (click log, order log, commission log)',
    'description': """
Warung Lakku Loyalty & Affiliate
================================

Two coupled features for the Warung Lakku Odoo storefront:

1. Voucher Diskon page (/voucher-diskon)
   - Lists 4 default voucher tiers (Rp 20k/200pts, 30k/300pts,
     50k/500pts, 100k/1000pts). Admin can edit/add tiers.
   - Shows logged-in user's current point balance.
   - User can exchange points for a voucher code (random string)
     when balance >= tier cost. Code is informational; admin
     applies the discount manually in the backend for now.
   - "Cara Mendapatkan Poin" section explains the affiliate share
     flow with the user's own affiliate link.

2. Simple affiliate system (6 tables total)
   - res.partner extended with: loyalty_points, affiliate_code
   - wl.loyalty.voucher.tier    (configurable tiers)
   - wl.loyalty.exchange        (exchange history)
   - wl.affiliate.click         (click log)
   - wl.affiliate.order         (order log: which sale.order came
                                 from which affiliate)
   - wl.affiliate.commission    (commission log: points earned
                                 by affiliate for each order)

Flow:
  1. Logged-in partner visits /voucher-diskon -> sees their
     affiliate_code (auto-generated first visit).
  2. On product page, partner sees a "Bagikan & Dapat Poin"
     widget with WA/FB/X/Copy buttons. Each builds URL:
       https://odoo.warunglakku.com/r/<code>?p=<product_id>
  3. Visitor clicks that link:
       - wl.affiliate.click record created (code, product, IP, UA)
       - 30-day cookie 'wl_aff_code' set
       - redirected to /shop/product/<slug>
  4. Visitor places an order:
       - sale.order.action_confirm() checks cookie
       - sets sale.order.affiliate_partner_id
       - creates wl.affiliate.order (state=pending)
  5. Order confirmed:
       - +N points to affiliate partner (default 50, configurable)
       - wl.affiliate.commission record created
       - wl.affiliate.order state=awarded
  6. Partner returns to /voucher-diskon, sees updated balance,
     can exchange for voucher.
""",
    'author': 'Warung Lakku',
    'website': 'https://warunglakku.com',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'website_sale',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/loyalty_voucher_tier_data.xml',
        'data/res_partner_affiliate_sequence.xml',
        'data/website_menu_data.xml',
        'views/loyalty_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/voucher_diskon_page.xml',
        'views/website_sale_product_share.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'warunglakku_loyalty/static/src/scss/loyalty.scss',
            'warunglakku_loyalty/static/src/js/affiliate_share.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
