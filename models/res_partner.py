# -*- coding: utf-8 -*-
"""Extend res.partner with loyalty points + affiliate code.

The affiliate_code is auto-generated the first time a partner
visits /voucher-diskon. Format: 8-char uppercase alphanumeric
(taken from sequence wl.affiliate.code.seq — defined in
data/res_partner_affiliate_sequence.xml).

Plain-text format means the affiliate URL is just:
    https://odoo.warunglakku.com/r/<code>?p=<product_id>
"""
import random
import string

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    loyalty_points = fields.Integer(
        string='Loyalty Points',
        default=0,
        help="Points earned via affiliate referrals. Spendable on "
             "/voucher-diskon for discount vouchers.",
    )
    affiliate_code = fields.Char(
        string='Affiliate Code',
        copy=False,
        index=True,
        help="Plain-text code used in /r/<code>?p=<id> URLs. "
             "Auto-generated on first /voucher-diskon visit.",
    )
    affiliate_click_count = fields.Integer(
        string='Affiliate Clicks',
        compute='_compute_affiliate_stats',
    )
    affiliate_order_count = fields.Integer(
        string='Affiliate Orders',
        compute='_compute_affiliate_stats',
    )
    affiliate_commission_total = fields.Integer(
        string='Total Commission Points',
        compute='_compute_affiliate_stats',
    )

    @api.depends()
    def _compute_affiliate_stats(self):
        Click = self.env['wl.affiliate.click']
        Order = self.env['wl.affiliate.order']
        Comm = self.env['wl.affiliate.commission']
        for p in self:
            p.affiliate_click_count = Click.search_count(
                [('affiliate_partner_id', '=', p.id)])
            p.affiliate_order_count = Order.search_count(
                [('affiliate_partner_id', '=', p.id)])
            p.affiliate_commission_total = sum(
                Comm.search([
                    ('affiliate_partner_id', '=', p.id),
                ]).mapped('points'))

    def ensure_affiliate_code(self):
        """Generate an 8-char code for this partner if missing.

        Public (no leading underscore) so it can be called from:
          - the /voucher-diskon controller (auto-generate on visit)
          - the /shop/product controller (auto-generate when viewing
            a product while logged in, so the share widget works)
          - the partner form button (admin can manually trigger)
        Idempotent — only writes once per partner.
        """
        self.ensure_one()
        if self.affiliate_code:
            return self.affiliate_code
        # 8-char uppercase alphanumeric (no ambiguous chars)
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        for _attempt in range(10):
            code = ''.join(random.choices(alphabet, k=8))
            if not self.env['res.partner'].sudo().search_count(
                    [('affiliate_code', '=', code)]):
                self.sudo().write({'affiliate_code': code})
                # Odoo 17 auto-flushes; explicit flush removed.
                return code
        # Extremely unlikely fallback
        code = 'WL' + ''.join(random.choices(string.digits, k=6))
        self.sudo().write({'affiliate_code': code})
        return code
