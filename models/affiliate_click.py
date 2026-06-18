# -*- coding: utf-8 -*-
"""Affiliate click log.

One record per /r/<code>?p=<product_id> hit. Captures:
  - which affiliate partner (looked up from code)
  - which product (optional — links can be generic)
  - visitor IP + user-agent (for fraud analysis)
  - timestamp

Indexes on (affiliate_partner_id, product_id, create_date) so the
admin dashboard can run "clicks in last 7 days by partner" queries
fast even at millions of rows.
"""
from odoo import fields, models


class AffiliateClick(models.Model):
    _name = 'wl.affiliate.click'
    _description = 'Warung Lakku Affiliate Click Log'
    _order = 'create_date DESC'

    affiliate_partner_id = fields.Many2one(
        'res.partner',
        string='Affiliate Partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    affiliate_code = fields.Char(
        string='Affiliate Code Used',
        help="The actual code in the URL (denormalized for debugging "
             "in case the partner later changes code).",
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        ondelete='set null',
        index=True,
    )
    product_template_id = fields.Many2one(
        'product.template',
        string='Product Template',
        ondelete='set null',
        index=True,
    )
    ip_address = fields.Char(string='IP Address', index=True)
    user_agent = fields.Char(string='User Agent')
    referer = fields.Char(string='Referer Header')
    converted_order_id = fields.Many2one(
        'sale.order',
        string='Converted To Order',
        ondelete='set null',
        help="Set when a sale.order is confirmed with this click's "
             "cookie still active.",
    )
