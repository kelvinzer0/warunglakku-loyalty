# -*- coding: utf-8 -*-
"""Extend sale.order with affiliate attribution.

Two new fields:
  - affiliate_partner_id   (the partner whose code brought the visitor)
  - affiliate_click_id     (the specific click that started the session)

On action_confirm(), we look at the request cookie 'wl_aff_code'
(set by /r/<code> redirect controller). If a partner matches, we
attach them to the order and create a wl.affiliate.order record
in state=pending.

Commission is awarded at this same point (immediate award). For
a more conservative policy (e.g. award only after payment), the
commission awarding can be moved to a payment hook later — see
the README in the manifest description.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

AFF_COOKIE_NAME = 'wl_aff_code'
AFF_COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 days


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    affiliate_partner_id = fields.Many2one(
        'res.partner',
        string='Affiliate Partner',
        copy=False,
        index=True,
        help="Partner whose affiliate link brought this customer. "
             "Set automatically on confirmation if the visitor had "
             "the wl_aff_code cookie.",
    )
    affiliate_click_id = fields.Many2one(
        'wl.affiliate.click',
        string='Affiliate Click Source',
        copy=False,
    )
    affiliate_order_log_id = fields.Many2one(
        'wl.affiliate.order',
        string='Affiliate Order Log',
        copy=False,
    )
    affiliate_state = fields.Selection(
        string='Affiliate State',
        related='affiliate_order_log_id.state',
        store=False,
        readonly=True,
    )

    def _get_affiliate_from_request(self):
        """Look up the affiliate partner from the current HTTP
        request's cookie/session. Returns a partner browse record
        (empty if not found, or if not in an HTTP context).

        Looks at:
          1. request cookie 'wl_aff_code'
          2. session 'wl_aff_code' (fallback if cookies disabled)

        Safe to call from cron / XML-RPC contexts where there is no
        active HTTP request — returns an empty recordset in that case.
        """
        try:
            from odoo.http import request as http_request
            req = http_request.httprequest
        except (ImportError, RuntimeError, AttributeError, TypeError):
            # No active HTTP request (e.g. cron, XML-RPC, tests)
            return self.env['res.partner']
        if req is None:
            return self.env['res.partner']
        code = req.cookies.get(AFF_COOKIE_NAME)
        if not code:
            try:
                code = http_request.session.get(AFF_COOKIE_NAME)
            except Exception:
                code = None
        if not code:
            return self.env['res.partner']
        Partner = self.env['res.partner'].sudo()
        return Partner.search([('affiliate_code', '=', code)], limit=1)

    def action_confirm(self):
        """Override to attach affiliate partner + create order log.

        Calls super() first (so the sale.order is actually confirmed),
        then if the current request has an affiliate cookie AND the
        order doesn't already have an affiliate_partner_id, attaches
        the affiliate and creates the wl.affiliate.order record. The
        commission is awarded immediately (state=awarded).
        """
        res = super().action_confirm()
        for order in self:
            if order.affiliate_partner_id:
                # Already attributed (e.g. admin set it manually)
                continue
            partner = self._get_affiliate_from_request()
            if not partner or partner.id == order.partner_id.id:
                # Self-referral — skip
                continue
            try:
                click = self.env['wl.affiliate.click'].sudo().search([
                    ('affiliate_partner_id', '=', partner.id),
                    ('converted_order_id', '=', False),
                ], order='create_date DESC', limit=1)
                log = self.env['wl.affiliate.order'].sudo().create({
                    'sale_order_id': order.id,
                    'affiliate_partner_id': partner.id,
                    'click_id': click.id if click else False,
                    'state': 'pending',
                })
                order.sudo().write({
                    'affiliate_partner_id': partner.id,
                    'affiliate_click_id': click.id if click else False,
                    'affiliate_order_log_id': log.id,
                })
                if click:
                    click.sudo().write({'converted_order_id': order.id})
                # Award commission immediately
                log.action_award()
                _logger.info(
                    '[WL_AFF] order %s attributed to affiliate %s '
                    '(code=%s) +%d points',
                    order.name, partner.id, partner.affiliate_code,
                    log.commission_points,
                )
            except Exception as e:
                _logger.exception(
                    '[WL_AFF] failed to log affiliate order %s: %s',
                    order.name, e)
        return res

    def action_cancel(self):
        """Override to cancel pending affiliate logs (clawback)."""
        res = super().action_cancel()
        for order in self:
            if order.affiliate_order_log_id:
                try:
                    order.affiliate_order_log_id.sudo().action_cancel()
                except Exception:
                    _logger.exception(
                        '[WL_AFF] failed to cancel affiliate log for '
                        'order %s', order.name)
        return res
