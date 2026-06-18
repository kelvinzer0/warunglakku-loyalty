# -*- coding: utf-8 -*-
"""Settings: default commission points + cookie duration + brand
URL for affiliate links (used by the share widget on the product
page to construct absolute URLs even when the page is loaded from
a different domain).
"""
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    wl_default_commission_points = fields.Integer(
        string='Default Affiliate Commission (points)',
        config_parameter='warunglakku_loyalty.default_commission_points',
        default=50,
        help="Points awarded to affiliate when their referred order "
             "is confirmed. 1 successful order = this many points.",
    )
    wl_affiliate_cookie_days = fields.Integer(
        string='Affiliate Cookie Duration (days)',
        config_parameter='warunglakku_loyalty.cookie_days',
        default=30,
        help="How long the wl_aff_code cookie persists in the "
             "visitor's browser after they click an affiliate link.",
    )
    wl_affiliate_base_url = fields.Char(
        string='Affiliate Base URL',
        config_parameter='warunglakku_loyalty.base_url',
        default='https://odoo.warunglakku.com',
        help="The public base URL used in affiliate share links. "
             "Should match your production Odoo domain.",
    )
