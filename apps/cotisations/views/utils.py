"""
Utilitaires pour les vues de cotisations.
"""
# Importations standard
import csv
import datetime
import io
import json
import logging
import os
import tempfile
import traceback
from datetime import datetime as dt
from decimal import Decimal, InvalidOperation

# Importations Django
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic import (
    View, TemplateView, ListView, DetailView,
    CreateView, UpdateView, DeleteView
)

# Importations conditionnelles
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Importations des applications
from apps.core.mixins import StaffRequiredMixin, TrashViewMixin, RestoreViewMixin
from apps.core.models import Statut
from apps.membres.models import Membre, TypeMembre, MembreTypeMembre

# Importations locales
from .. import export_utils
from ..models import (
    Cotisation, Paiement, ModePaiement, BaremeCotisation,
    Rappel, HistoriqueCotisation, ConfigurationCotisation,
    RAPPEL_ETAT_PLANIFIE, RAPPEL_ETAT_ENVOYE, RAPPEL_ETAT_ECHOUE, RAPPEL_ETAT_LU
)
from ..forms import (
    CotisationForm, PaiementForm, BaremeCotisationForm,
    RappelForm, CotisationSearchForm, ImportCotisationsForm,
    ConfigurationCotisationForm
)

# Configuration du logging
logger = logging.getLogger(__name__)


class ExtendedJSONEncoder(DjangoJSONEncoder):
    """
    Encodeur JSON personnalisé pour gérer les types Python spécifiques
    comme Decimal, date et datetime correctement.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)
