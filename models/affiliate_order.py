# -*- coding: utf-8 -*-
"""Affiliate order log.

One record per sale.order that was placed by a visitor with an
affiliate cookie active. Created in sale_order.action_confirm()
override.

State machine:
  pending  -> awarded (order confirmed, points credited to affiliate)
  pending  -> cancelled (order cancelled before confirmation)
  awarded  -> clawed_back (rare: admin manually revokes commission)
"""
from odoo import _, api, fields, models


class AffiliateOrder(models.Model):
    _name = 'wl.affiliate.order'
    _description = 'Warung Lakku Affiliate Order Log'
    _order = 'create_date DESC'
    _rec_name = 'sale_order_id'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    affiliate_partner_id = fields.Many2one(
        'res.partner',
        string='Affiliate Partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    click_id = fields.Many2one(
        'wl.affiliate.click',
        string='Source Click',
        ondelete='set null',
    )
    commission_points = fields.Integer(
        string='Commission Points',
        default=lambda self: int(self.env['ir.config_parameter']
            .sudo().get_param(
                'warunglakku_loyalty.default_commission_points', '50')),
    )
    commission_id = fields.Many2one(
        'wl.affiliate.commission',
        string='Commission Log Entry',
        ondelete='set null',
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('awarded', 'Awarded'),
        ('cancelled', 'Cancelled'),
        ('clawed_back', 'Clawed Back'),
    ], string='State', default='pending', required=True, index=True)
    order_amount_total = fields.Monetary(
        string='Order Total',
        related='sale_order_id.amount_total',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    notes = fields.Text(string='Notes')

    def action_award(self):
        """Award commission_points to affiliate_partner_id.

        Creates a wl.affiliate.commission record and increments the
        partner's loyalty_points. Idempotent — if commission_id is
        already set, do nothing.
        """
        Commission = self.env['wl.affiliate.commission']
        for rec in self:
            if rec.state == 'awarded' and rec.commission_id:
                continue
            if rec.state not in ('pending', 'awarded'):
                continue
            comm = Commission.sudo().create({
                'affiliate_partner_id': rec.affiliate_partner_id.id,
                'sale_order_id': rec.sale_order_id.id,
                'affiliate_order_id': rec.id,
                'points': rec.commission_points,
                'reason': _("Commission for referred order %s") %
                          rec.sale_order_id.name,
            })
            rec.affiliate_partner_id.sudo().write({
                'loyalty_points':
                    rec.affiliate_partner_id.loyalty_points +
                    rec.commission_points,
            })
            rec.write({
                'state': 'awarded',
                'commission_id': comm.id,
            })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'awarded' and rec.commission_id:
                # Clawback: deduct the points back
                rec.affiliate_partner_id.sudo().write({
                    'loyalty_points': max(0,
                        rec.affiliate_partner_id.loyalty_points -
                        rec.commission_points),
                })
                rec.commission_id.sudo().write({
                    'state': 'clawed_back',
                })
            rec.state = 'cancelled'
