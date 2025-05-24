# apps/cotisations/utils.py
import json
from decimal import Decimal
from django.utils.functional import Promise
from django.utils.encoding import force_str

class DecimalJSONEncoder(json.JSONEncoder):
    """
    Encodeur JSON personnalisé capable de sérialiser les objets Decimal.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
    
class ExtendedJSONEncoder(json.JSONEncoder):
    """
    Encodeur JSON personnalisé pour gérer les types Python spécifiques
    comme Decimal, date, datetime et les textes traduits correctement.
    """
    def default(self, obj):
        from django.utils.functional import Promise
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, Promise):
            # Pour gérer les objets de traduction
            return str(obj)
        return super().default(obj)
