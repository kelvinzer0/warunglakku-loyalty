# -*- coding: utf-8 -*-
"""Affiliate commission log.

Immutable log of every points-credit awarded to an affiliate.
One row per affiliate_order.action_award() call.

This is the table the user explicitly asked for — "Commission Log"
— kept separate from wl.affiliate.order so that:
  - points history is fully auditable (one row per credit)
  - clawbacks are visible (state=clawed_back, original row preserved)
  - the partner dashboard can show a simple chronological list
"""
from odoo import fields, models


class AffiliateCommission(models.Model):
    _name = 'wl.affiliate.commission'
    _description = 'Warung Lakku Affiliate Commission Log'
    _order = 'create_date DESC'
    _rec_name = 'affiliate_partner_id'

    affiliate_partner_id = fields.Many2one(
        'res.partner',
        string='Affiliate Partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        ondelete='cascade',
        index=True,
    )
    affiliate_order_id = fields.Many2one(
        'wl.affiliate.order',
        string='Affiliate Order',
        ondelete='set null',
    )
    points = fields.Integer(
        string='Points Awarded',
        required=True,
    )
    reason = fields.Char(string='Reason')
    state = fields.Selection([
        ('active', 'Active'),
        ('clawed_back', 'Clawed Back'),
    ], string='State', default='active', required=True, index=True)
