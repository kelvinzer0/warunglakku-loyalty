# -*- coding: utf-8 -*-
"""Voucher tier model.

Each tier = a fixed-price voucher redeemable for X points.
e.g.  Rp 20,000 voucher costs 200 points
       Rp 30,000 voucher costs 300 points
       Rp 50,000 voucher costs 500 points
       Rp 100,000 voucher costs 1000 points

The voucher_value is informational (displayed as "Rp 20.000").
The actual discount is applied by admin manually in the backend
using the voucher_code generated when partner exchanges points.
"""
from odoo import api, fields, models


class LoyaltyVoucherTier(models.Model):
    _name = 'wl.loyalty.voucher.tier'
    _description = 'Warung Lakku Loyalty Voucher Tier'
    _order = 'point_cost ASC'

    name = fields.Char(
        string='Tier Name',
        required=True,
        translate=True,
        help="Display name e.g. 'Voucher Rp 20.000'",
    )
    voucher_value = fields.Monetary(
        string='Voucher Value (Rp)',
        currency_field='currency_id',
        required=True,
        help="Nominal discount value in IDR.",
    )
    point_cost = fields.Integer(
        string='Point Cost',
        required=True,
        help="Points deducted from partner balance on exchange.",
    )
    active = fields.Boolean(string='Active', default=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    exchange_count = fields.Integer(
        string='Total Exchanges',
        compute='_compute_exchange_count',
    )

    @api.depends()
    def _compute_exchange_count(self):
        Exchange = self.env['wl.loyalty.exchange']
        for tier in self:
            tier.exchange_count = Exchange.search_count(
                [('voucher_tier_id', '=', tier.id)])

    def name_get(self):
        res = []
        for tier in self:
            res.append((tier.id,
                f"{tier.name} ({tier.point_cost} poin)"))
        return res
