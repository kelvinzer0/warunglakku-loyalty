# -*- coding: utf-8 -*-
"""Affiliate order log.

One record per sale.order that was placed by a visitor with an
affiliate cookie active. Created in sale_order.action_confirm()
override.

Commission calculation (v1.1.0+):
    points = floor( order_total × commission_rate% ÷ 100 ÷ points_per_rupiah )

Example with default config (1% rate, 100 Rp/point):
    order Rp 10.000  → 1% × 10.000 = Rp 100  → 1 point
    order Rp 100.000 → 1% × 100.000 = Rp 1000 → 10 points
    order Rp 2.000.000 → 1% × 2.000.000 = Rp 20.000 → 200 points

If sale.order is missing or amount_total = 0 (e.g. manual admin
entry), falls back to wl_default_commission_points (legacy 50).

State machine:
  pending  -> awarded (order confirmed, points credited to affiliate)
  pending  -> cancelled (order cancelled before confirmation)
  awarded  -> clawed_back (rare: admin manually revokes commission)
"""
import logging
import math

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


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
        default=0,
        help="Auto-computed on create from order_total × "
             "commission_rate% ÷ points_per_rupiah. Falls back to "
             "the legacy default_commission_points config if "
             "order_total is 0.",
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

    # ----------------------------------------------------------
    # Commission calculation
    # ----------------------------------------------------------
    @api.model
    def _get_commission_rate_percent(self):
        """Read commission_rate_percent from config (default 1.0)."""
        try:
            val = self.env['ir.config_parameter'].sudo().get_param(
                'warunglakku_loyalty.commission_rate_percent', '1.0')
            rate = float(val or '1.0')
            return rate if rate >= 0 else 1.0
        except (TypeError, ValueError):
            return 1.0

    @api.model
    def _get_points_per_rupiah(self):
        """Read points_per_rupiah from config (default 100)."""
        try:
            val = self.env['ir.config_parameter'].sudo().get_param(
                'warunglakku_loyalty.points_per_rupiah', '100')
            ppr = int(val or '100')
            return ppr if ppr > 0 else 100
        except (TypeError, ValueError):
            return 100

    @api.model
    def _get_legacy_default_points(self):
        """Read legacy default_commission_points (default 50)."""
        try:
            val = self.env['ir.config_parameter'].sudo().get_param(
                'warunglakku_loyalty.default_commission_points', '50')
            return int(val or '50')
        except (TypeError, ValueError):
            return 50

    def _compute_commission_points(self):
        """Compute points for THIS affiliate order record.

        Formula:
            points = floor( order_total × rate% ÷ 100 ÷ points_per_rupiah )

        If order_total is 0 or sale.order missing, fall back to the
        legacy default_commission_points config value.
        """
        self.ensure_one()
        order_total = 0.0
        if self.sale_order_id:
            order_total = float(self.sale_order_id.amount_total or 0.0)
        if order_total <= 0:
            return self._get_legacy_default_points()
        rate = self._get_commission_rate_percent()
        ppr = self._get_points_per_rupiah()
        # commission in IDR = order_total × rate / 100
        commission_rp = order_total * rate / 100.0
        # points = floor(commission_rp / ppr)
        points = int(math.floor(commission_rp / ppr))
        _logger.info(
            '[WL_AFF] commission calc: order=%s total=%.2f rate=%.2f%% '
            'ppr=%d → commission_rp=%.2f → points=%d',
            self.sale_order_id.name, order_total, rate, ppr,
            commission_rp, points,
        )
        return points

    # ----------------------------------------------------------
    # CRUD override
    # ----------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        """Override to auto-compute commission_points on create.

        If the caller didn't pass an explicit commission_points (or
        passed 0), we compute it from the linked sale.order's
        amount_total using the configured rate + ppr.
        """
        records = super().create(vals_list)
        for rec in records:
            if not rec.commission_points:
                try:
                    rec.commission_points = rec._compute_commission_points()
                except Exception as e:
                    _logger.exception(
                        '[WL_AFF] commission calc failed for order %s: %s',
                        rec.sale_order_id.name if rec.sale_order_id else '?',
                        e)
                    rec.commission_points = rec._get_legacy_default_points()
        return records

    # ----------------------------------------------------------
    # State transitions
    # ----------------------------------------------------------
    def action_award(self):
        """Award commission_points to affiliate_partner_id.

        Creates a wl.affiliate.commission record and increments the
        partner's loyalty_points. Idempotent — if commission_id is
        already set, do nothing.

        Before awarding, recomputes commission_points from the
        current order_total (in case the order was edited between
        create() and award()).
        """
        Commission = self.env['wl.affiliate.commission']
        for rec in self:
            if rec.state == 'awarded' and rec.commission_id:
                continue
            if rec.state not in ('pending', 'awarded'):
                continue
            # Recompute in case order_total changed since create()
            try:
                rec.commission_points = rec._compute_commission_points()
            except Exception as e:
                _logger.exception(
                    '[WL_AFF] recompute failed on award for order %s: %s',
                    rec.sale_order_id.name if rec.sale_order_id else '?', e)
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
