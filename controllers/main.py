# -*- coding: utf-8 -*-
"""Public controllers for the loyalty/affiliate module.

Routes:
  GET  /voucher-diskon
       Renders the main page: voucher tiers, partner's point balance,
       partner's affiliate code, "how to earn points" guide, recent
       commission history. Auto-generates an affiliate_code for the
       logged-in partner if missing.

  POST /voucher-diskon/exchange
       Exchange points for a voucher tier. Form fields:
         tier_id = id of wl.loyalty.voucher.tier
       On success: redirect back to /voucher-diskon with
       ?exchanged=<exchange_id> so the page can flash the new code.
       On failure (insufficient points, not logged in):
       redirect with ?error=<code>

  GET  /aff/<string:code>
       Affiliate redirect endpoint. Looks up the partner by code,
       logs the click, sets the wl_aff_code cookie (30 days), and
       redirects to:
         - /shop/product/<slug> if ?p=<product_id> is provided
         - /shop if no product specified

       NOTE: We use /aff/ instead of /r/ because Odoo's
       website_link_tracker module already registers /r/<code>
       for its own URL shortener, which would shadow our route.
"""
import logging
import werkzeug

from odoo import _, http
from odoo.http import request

_logger = logging.getLogger(__name__)

AFF_COOKIE_NAME = 'wl_aff_code'


class WarungLakkuLoyalty(http.Controller):

    @http.route(['/voucher-diskon'], type='http', auth='public',
                website=True, sitemap=True)
    def voucher_diskon_page(self, **kw):
        """Main /voucher-diskon page."""
        partner = request.env.user.partner_id
        is_logged_in = (request.env.user._is_public() is False)

        if is_logged_in:
            # Auto-generate affiliate code on first visit
            partner.sudo().ensure_affiliate_code()
            partner = partner.sudo()
        else:
            partner = request.env['res.partner']

        tiers = request.env['wl.loyalty.voucher.tier'].sudo().search(
            [('active', '=', True)], order='point_cost ASC')

        # Recent exchanges (last 5) for this partner
        recent_exchanges = request.env['wl.loyalty.exchange'].sudo()
        recent_commissions = request.env['wl.affiliate.commission'].sudo()
        if is_logged_in and partner:
            recent_exchanges = recent_exchanges.search(
                [('partner_id', '=', partner.id)], limit=5)
            recent_commissions = recent_commissions.search(
                [('affiliate_partner_id', '=', partner.id),
                 ('state', '=', 'active')], limit=5)

        # Flash data
        exchanged_id = kw.get('exchanged')
        exchanged_record = None
        if exchanged_id and exchanged_id.isdigit():
            exchanged_record = request.env['wl.loyalty.exchange'].sudo().browse(
                int(exchanged_id)).exists()
        error = kw.get('error')

        base_url = request.env['ir.config_parameter'].sudo().get_param(
            'warunglakku_loyalty.base_url',
            'https://odoo.warunglakku.com')

        values = {
            'is_logged_in': is_logged_in,
            'partner': partner,
            'tiers': tiers,
            'recent_exchanges': recent_exchanges,
            'recent_commissions': recent_commissions,
            'exchanged': exchanged_record,
            'error': error,
            'base_url': base_url,
        }
        return request.render(
            'warunglakku_loyalty.voucher_diskon_page', values)

    @http.route(['/voucher-diskon/exchange'], type='http', auth='user',
                methods=['POST'], website=True, csrf=True)
    def voucher_diskon_exchange(self, **kw):
        """Exchange points for a voucher tier."""
        partner = request.env.user.partner_id
        tier_id = kw.get('tier_id')
        if not tier_id or not str(tier_id).isdigit():
            return request.redirect('/voucher-diskon?error=invalid_tier')
        tier = request.env['wl.loyalty.voucher.tier'].sudo().browse(
            int(tier_id)).exists()
        if not tier or not tier.active:
            return request.redirect('/voucher-diskon?error=invalid_tier')
        if partner.loyalty_points < tier.point_cost:
            return request.redirect(
                '/voucher-diskon?error=insufficient_points')

        try:
            exchange = request.env['wl.loyalty.exchange'].sudo().create({
                'partner_id': partner.id,
                'voucher_tier_id': tier.id,
                'state': 'draft',
            })
        except Exception as e:
            _logger.exception('[WL_LOYALTY] exchange failed: %s', e)
            return request.redirect('/voucher-diskon?error=server_error')

        return request.redirect(
            '/voucher-diskon?exchanged=%d' % exchange.id)

    @http.route(['/aff/<string:code>'], type='http', auth='public',
                website=True, sitemap=False)
    def affiliate_redirect(self, code, **kw):
        """Affiliate redirect + click log.

        URL format:
            /aff/<code>                 -> redirect to /shop
            /aff/<code>?p=<product_id>  -> redirect to that product page
        """
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('affiliate_code', '=', code)], limit=1)
        if not partner:
            _logger.info('[WL_AFF] unknown affiliate code: %s', code)
            return request.redirect('/shop')

        # Log the click
        product_id = kw.get('p')
        product = request.env['product.product']
        product_template = request.env['product.template']
        if product_id and str(product_id).isdigit():
            product = request.env['product.product'].sudo().browse(
                int(product_id)).exists()
            if product:
                product_template = product.product_tmpl_id

        try:
            http_req = request.httprequest
            ip = (http_req.headers.get('X-Forwarded-For', '')
                  or http_req.remote_addr or '')
            ip = ip.split(',')[0].strip()[:64]
            ua = http_req.headers.get('User-Agent', '')[:512]
            ref = http_req.headers.get('Referer', '')[:512]
            click = request.env['wl.affiliate.click'].sudo().create({
                'affiliate_partner_id': partner.id,
                'affiliate_code': code,
                'product_id': product.id if product else False,
                'product_template_id': (product_template.id
                    if product_template else False),
                'ip_address': ip,
                'user_agent': ua,
                'referer': ref,
            })
        except Exception as e:
            _logger.exception('[WL_AFF] click log failed: %s', e)
            click = request.env['wl.affiliate.click']

        # Set cookie + session
        cookie_days = int(request.env['ir.config_parameter']
            .sudo().get_param('warunglakku_loyalty.cookie_days', '30'))
        try:
            request.session[AFF_COOKIE_NAME] = code
        except Exception:
            pass

        # Build redirect URL
        if product_template:
            target = '/shop/product/%s' % product_template.id
        else:
            target = '/shop'

        # Use werkzeug redirect so we can set the cookie on the response
        response = werkzeug.utils.redirect(target, code=302)
        try:
            response.set_cookie(
                AFF_COOKIE_NAME, code,
                max_age=cookie_days * 24 * 3600,
                httponly=True, samesite='Lax',
            )
        except Exception as e:
            _logger.warning('[WL_AFF] set_cookie failed: %s', e)
        return response
