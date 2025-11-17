# Plan de Refonte : Membre → User Workflow

## 🎯 Objectif

Inverser le workflow de création : d'abord créer un CustomUser, puis attacher un profil Membre.

## 📋 Modifications nécessaires

### Phase 1 : Modèle Membre - Suppression champs dupliqués

**Fichier** : `apps/membres/models.py`

**Actions** :
1. Supprimer les champs :
   - `nom` (CharField)
   - `prenom` (CharField)
   - `email` (EmailField)
   - `telephone` (CharField)

2. Ajouter des propriétés (@property) :
   ```python
   @property
   def nom(self):
       return self.utilisateur.last_name if self.utilisateur else ''

   @property
   def prenom(self):
       return self.utilisateur.first_name if self.utilisateur else ''

   @property
   def email(self):
       return self.utilisateur.email if self.utilisateur else ''

   @property
   def telephone(self):
       return self.utilisateur.telephone if self.utilisateur else ''
   ```

3. Créer migration :
   ```bash
   python manage.py makemigrations membres --name remove_duplicate_fields
   python manage.py migrate
   ```

**⚠️ ATTENTION** : Migration destructive ! Avant de l'appliquer :
- Vérifier que tous les membres existants ont un utilisateur lié
- Backup de la base de données

### Phase 2 : Formulaire MembreForm

**Fichier** : `apps/membres/forms.py`

**Actions** :
1. Supprimer champs :
   - `creer_compte` (BooleanField)
   - `password` (CharField)
   - `password_confirm` (CharField)

2. Ajouter champ utilisateur :
   ```python
   utilisateur = forms.ModelChoiceField(
       queryset=CustomUser.objects.filter(membre__isnull=True),
       required=True,
       label=_("Utilisateur"),
       help_text=_("Sélectionner un utilisateur existant"),
       widget=autocomplete.ModelSelect2(
           url='accounts:user-autocomplete',
           attrs={'data-placeholder': _('Rechercher un utilisateur...')}
       )
   )
   ```

3. Modifier Meta.fields :
   - Supprimer : 'nom', 'prenom', 'email', 'telephone'
   - Ajouter : 'utilisateur' en premier
   - Garder : adresse, code_postal, ville, pays, date_adhesion, date_naissance, langue, statut, accepte_mail, accepte_sms, commentaires, photo

4. Supprimer validation password dans `clean()`

### Phase 3 : Vue Autocomplete pour utilisateurs

**Nouveau fichier** : `apps/accounts/views.py` (ou ajouter dans existant)

**Actions** :
```python
from dal import autocomplete
from apps.accounts.models import CustomUser

class UserAutocompleteView(autocomplete.Select2QuerySetView):
    """Vue autocomplete pour sélection utilisateur sans profil membre"""

    def get_queryset(self):
        # Seulement utilisateurs sans membre
        qs = CustomUser.objects.filter(membre__isnull=True)

        if self.q:
            qs = qs.filter(
                Q(username__icontains=self.q) |
                Q(email__icontains=self.q) |
                Q(first_name__icontains=self.q) |
                Q(last_name__icontains=self.q)
            )

        return qs

    def get_result_label(self, user):
        """Format: jean.dupont (Jean Dupont - jean.dupont@example.com)"""
        name = f"{user.first_name} {user.last_name}".strip() or "Sans nom"
        return f"{user.username} ({name} - {user.email})"
```

**URLs** : `apps/accounts/urls.py`
```python
path('user-autocomplete/', UserAutocompleteView.as_view(), name='user-autocomplete'),
```

### Phase 4 : Vue MembreCreateView

**Fichier** : `apps/membres/views.py`

**Actions** :
1. Simplifier `form_valid()` :
   ```python
   def form_valid(self, form):
       try:
           # Extraire données
           types_membre = form.cleaned_data.pop('types_membre', [])

           # Créer seulement le membre (utilisateur déjà lié via formulaire)
           membre = form.save()

           # Ajouter types de membre
           if types_membre:
               for type_membre in types_membre:
                   membre.ajouter_type(type_membre)

           # Historique
           HistoriqueMembre.objects.create(
               membre=membre,
               utilisateur=self.request.user,
               action='creation',
               description=_("Création du profil membre pour l'utilisateur %(username)s") % {
                   'username': membre.utilisateur.username
               }
           )

           messages.success(
               self.request,
               _("Le profil membre pour %(nom)s a été créé avec succès.") % {
                   'nom': membre.nom_complet
               }
           )

           return redirect(membre.get_absolute_url())
       except Exception as e:
           logger.error(f"Erreur création profil membre: {str(e)}", exc_info=True)
           messages.error(self.request, _("Erreur: %(error)s") % {'error': str(e)})
           return self.form_invalid(form)
   ```

2. Ne plus utiliser `UserCreationService.creer_membre_avec_compte()`

### Phase 5 : Template

**Fichier** : `apps/membres/templates/membres/membre_form.html`

**Actions** :
1. Ajouter section utilisateur en haut :
   ```html
   <div class="form-group">
       <label>{{ form.utilisateur.label }}</label>
       {{ form.utilisateur }}
       {% if form.utilisateur.help_text %}
           <small class="form-text text-muted">{{ form.utilisateur.help_text }}</small>
       {% endif %}
       {% if form.utilisateur.errors %}
           <div class="invalid-feedback d-block">{{ form.utilisateur.errors }}</div>
       {% endif %}
   </div>

   <!-- Affichage infos utilisateur sélectionné -->
   <div id="user-info" class="alert alert-info" style="display: none;">
       <h5>Informations utilisateur</h5>
       <dl class="row">
           <dt class="col-sm-3">Nom d'utilisateur:</dt>
           <dd class="col-sm-9" id="user-username"></dd>

           <dt class="col-sm-3">Nom complet:</dt>
           <dd class="col-sm-9" id="user-fullname"></dd>

           <dt class="col-sm-3">Email:</dt>
           <dd class="col-sm-9" id="user-email"></dd>

           <dt class="col-sm-3">Téléphone:</dt>
           <dd class="col-sm-9" id="user-telephone"></dd>
       </dl>
   </div>
   ```

2. Ajouter JavaScript pour afficher infos utilisateur :
   ```javascript
   $(document).ready(function() {
       $('#id_utilisateur').on('change', function() {
           const userId = $(this).val();
           if (userId) {
               // Récupérer infos utilisateur via AJAX
               $.ajax({
                   url: `/accounts/api/user/${userId}/`,
                   success: function(data) {
                       $('#user-username').text(data.username);
                       $('#user-fullname').text(`${data.first_name} ${data.last_name}`);
                       $('#user-email').text(data.email);
                       $('#user-telephone').text(data.telephone || 'Non renseigné');
                       $('#user-info').show();
                   }
               });
           } else {
               $('#user-info').hide();
           }
       });
   });
   ```

3. Supprimer les champs : nom, prenom, email, telephone, creer_compte, password

### Phase 6 : API endpoint pour infos utilisateur

**Fichier** : `apps/accounts/views.py`

**Actions** :
```python
from django.http import JsonResponse
from django.views import View

class UserInfoAPIView(View):
    """API pour récupérer infos utilisateur"""

    def get(self, request, user_id):
        try:
            user = CustomUser.objects.get(pk=user_id)
            return JsonResponse({
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'telephone': user.telephone or '',
            })
        except CustomUser.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
```

**URLs** :
```python
path('api/user/<int:user_id>/', UserInfoAPIView.as_view(), name='user-info-api'),
```

### Phase 7 : Dépendances

**Installer** :
```bash
pip install django-autocomplete-light
```

**settings.py** :
```python
INSTALLED_APPS = [
    # ...
    'dal',
    'dal_select2',
    # ...
]
```

### Phase 8 : Tests

**Fichier** : `apps/membres/tests/test_views.py`

**Actions** :
1. Modifier tests existants :
   - Ne plus tester création avec compte
   - Tester seulement création profil membre depuis utilisateur existant

2. Ajouter nouveaux tests :
   ```python
   def test_create_membre_from_existing_user(self):
       """Test création profil membre depuis utilisateur existant"""
       # Créer un utilisateur sans membre
       user = CustomUser.objects.create_user(
           username='test.user',
           email='test@example.com',
           password='test123'
       )

       # Créer membre
       response = self.client.post(reverse('membres:membre_nouveau'), {
           'utilisateur': user.id,
           'date_adhesion': '2025-01-01',
           # ... autres champs
       })

       # Vérifications
       self.assertEqual(response.status_code, 302)
       membre = Membre.objects.get(utilisateur=user)
       self.assertEqual(membre.email, 'test@example.com')

   def test_cannot_create_membre_for_user_with_membre(self):
       """Test qu'on ne peut pas créer 2 profils membre pour même user"""
       # Créer user + membre
       user, membre = self.create_user_with_membre()

       # Vérifier que l'utilisateur n'apparaît pas dans la liste
       form = MembreForm()
       self.assertNotIn(user, form.fields['utilisateur'].queryset)
   ```

### Phase 9 : Migration données existantes

**Script** : `apps/membres/management/commands/verify_membre_user_link.py`

**Actions** :
```python
from django.core.management.base import BaseCommand
from apps.membres.models import Membre

class Command(BaseCommand):
    help = 'Vérifie que tous les membres ont un utilisateur lié'

    def handle(self, *args, **options):
        membres_sans_user = Membre.objects.filter(utilisateur__isnull=True)

        if membres_sans_user.exists():
            self.stdout.write(self.style.ERROR(
                f"ATTENTION: {membres_sans_user.count()} membres sans utilisateur!"
            ))
            for membre in membres_sans_user:
                self.stdout.write(f"  - {membre.nom_complet} (ID: {membre.id})")
        else:
            self.stdout.write(self.style.SUCCESS(
                "OK: Tous les membres ont un utilisateur lié"
            ))
```

**Exécuter avant migration** :
```bash
python manage.py verify_membre_user_link
```

## 📅 Ordre d'exécution

1. ✅ Vérifier liens membres-utilisateurs existants
2. ✅ Installer django-autocomplete-light
3. ✅ Créer API endpoint user info
4. ✅ Créer vue autocomplete
5. ✅ Modifier formulaire MembreForm
6. ✅ Modifier vue MembreCreateView
7. ✅ Modifier template
8. ✅ Modifier modèle Membre (propriétés)
9. ✅ Créer et appliquer migration
10. ✅ Mettre à jour tests
11. ✅ Tester manuellement

## ⚠️ Risques et précautions

1. **Migration destructive** : Sauvegarde BD avant migration
2. **Membres sans user** : Script de vérification obligatoire
3. **Backwards compatibility** : Les anciens membres fonctionneront car ils ont déjà utilisateur lié
4. **Formulaire existant** : Le formulaire d'édition doit aussi être adapté

## 🧪 Tests manuels

1. Créer utilisateur via `/admin/accounts/customuser/add/`
2. Aller sur `/membres/nouveau/`
3. Rechercher l'utilisateur dans autocomplete
4. Sélectionner → vérifier que les infos s'affichent
5. Remplir champs spécifiques membre
6. Soumettre → vérifier création
7. Vérifier qu'on ne peut plus sélectionner cet utilisateur

## 📝 Documentation à mettre à jour

- `apps/membres/README.md` - Si existe
- `INSTALLATION_ET_TESTS.md` - Section membres
- Docstrings dans le code
