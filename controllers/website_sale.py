# -*- coding: utf-8 -*-
"""Extend WebsiteSale product controller to expose affiliate code to
the product page QWeb context.

We don't change any behaviour — we just make sure the template has
access to:
  - the logged-in partner's affiliate_code (or empty if not logged in)
  - the absolute base_url for building share links
  - the current product's id (already in context, but expose cleanly)

The actual share widget is rendered by an xpath on
website_sale.product template (see views/website_sale_product_share.xml).
"""
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleAffiliate(WebsiteSale):

    @http.route()
    def product(self, product, category='', search='', **kwargs):
        """Hook /shop/product/<id-or-slug> to inject affiliate context.

        Odoo 17 changed the WebsiteSale.product() signature: the
        first positional arg is now `product` (which can be either
        an int ID or a slug string), not `product_id`.
        """
        response = super().product(
            product, category=category, search=search, **kwargs)
        try:
            if hasattr(response, 'qcontext'):
                qctx = response.qcontext
                partner = http.request.env.user.partner_id
                is_logged_in = (http.request.env.user._is_public() is False)
                if is_logged_in and partner:
                    partner.sudo().ensure_affiliate_code()
                    qctx['wl_affiliate_code'] = partner.affiliate_code
                    qctx['wl_affiliate_partner_id'] = partner.id
                else:
                    qctx['wl_affiliate_code'] = ''
                    qctx['wl_affiliate_partner_id'] = False
                qctx['wl_is_logged_in'] = is_logged_in
                qctx['wl_base_url'] = http.request.env[
                    'ir.config_parameter'].sudo().get_param(
                    'warunglakku_loyalty.base_url',
                    'https://odoo.warunglakku.com')
        except Exception as e:
            # Don't break the product page if affiliate context fails
            import logging
            logging.getLogger(__name__).exception(
                '[WL_AFF] product() context inject failed: %s', e)
        return response
