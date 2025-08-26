from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class Loading(models.AbstractModel):
    _name = 'loading.mixin'
    is_loading = fields.Boolean("Loading", default=True)
    