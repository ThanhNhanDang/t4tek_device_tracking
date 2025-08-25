# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import logging
import pprint
import urllib.parse
import uuid
import pytz
import requests as pyreq
import json
import requests

from werkzeug.exceptions import Forbidden  # type: ignore
from odoo import _, http, tools
from odoo.http import request
from odoo.exceptions import AccessError, MissingError, ValidationError

from datetime import datetime, timedelta
from odoo.fields import Command
from odoo.addons.payment.controllers import portal as payment_portal
_logger = logging.getLogger(__name__)

class MainController(http.Controller):
    main_url = "/api/v1/tracking"
    
    
    @http.route(main_url, type='json', auth='public', methods=['POST'])
    def tracking(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            tid = data.get('tid')
            if not tid:
                return {'error': 'Missing TID in request payload'}

            card = request.env['stock.receipt.card'].sudo().search([('name', '=', tid)], limit=1)
            if not card:
                return {'error': f'Card with TID {tid} not found'}
            if card.state == "in" and card.status == "input":
                if card.company_id:
                    request.env['bus.bus'].sudo()._sendone(
                        "12344",
                        'card_notification',
                        {
                        }
                    )
                    _logger.info(str(card.company_id.id))
                return {'error': f'Card with TID {tid} is already in input state'}
            elif card.state != "in":
                # card.action_import_cards()
                card.state = "in"
            elif card.state == "in" and card.status != "input":
                card.state = "out"
            return {
                'status': 'success',
                'message': 'Order synced successfully',
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}