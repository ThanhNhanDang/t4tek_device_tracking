import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
_logger = logging.getLogger(__name__)


class Stocklot(models.Model):
    _inherit = 'stock.lot'
   
    def create(self, vals):
        return super(Stocklot,self).create(vals)