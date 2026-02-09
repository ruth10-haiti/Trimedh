# Application Consultation - Documentation Complète

## 📋 Vue d'ensemble

Application complète de gestion des consultations médicales avec Django (Backend) et Flutter (Frontend).

## 🔧 Backend Django

### Modèle (déjà existant)
```python
# medical/models.py
class Consultation(models.Model):
    consultation_id = models.AutoField(primary_key=True)
    tenant = models.ForeignKey('gestion_tenants.Tenant', on_delete=models.CASCADE)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE)
    medecin = models.ForeignKey(Medecin, on_delete=models.CASCADE)
    rendez_vous = models.ForeignKey('rendez_vous.RendezVous', on_delete=models.SET_NULL, null=True)
    date_consultation = models.DateTimeField()
    motif = models.CharField(max_length=255)
    diagnostic_principal = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
```

### API Endpoints

#### 1. Liste des consultations
```
GET /api/medical/consultations/
```
**Paramètres de requête:**
- `date_from` : Date de début (YYYY-MM-DD)
- `date_to` : Date de fin (YYYY-MM-DD)
- `patient_id` : ID du patient
- `medecin_id` : ID du médecin

**Réponse:**
```json
{
  "count": 10,
  "results": [
    {
      "consultation_id": 1,
      "tenant": 1,
      "patient": 5,
      "patient_detail": {
        "patient_id": 5,
        "nom": "Dupont",
        "prenom": "Jean"
      },
      "medecin": 2,
      "medecin_detail": {
        "medecin_id": 2,
        "nom": "Martin",
        "prenom": "Sophie"
      },
      "date_consultation": "2024-01-15T10:30:00Z",
      "motif": "Consultation de routine",
      "diagnostic_principal": "RAS",
      "notes": "Patient en bonne santé"
    }
  ]
}
```

#### 2. Créer une consultation
```
POST /api/medical/consultations/
```
**Body:**
```json
{
  "patient_id": 5,
  "medecin_id": 2,
  "rendez_vous_id": 10,
  "date_consultation": "2024-01-15T10:30:00Z",
  "motif": "Consultation de routine",
  "diagnostic_principal": "RAS",
  "notes": "Patient en bonne santé"
}
```

#### 3. Mettre à jour une consultation
```
PATCH /api/medical/consultations/{id}/
```
**Body:**
```json
{
  "diagnostic_principal": "Grippe saisonnière",
  "notes": "Repos recommandé"
}
```

#### 4. Consultations du jour
```
GET /api/medical/consultations/aujourd_hui/
```
**Réponse:**
```json
{
  "date": "2024-01-15",
  "total": 5,
  "consultations": [...]
}
```

#### 5. Mes consultations (médecin)
```
GET /api/medical/consultations/mes_consultations/
```

#### 6. Statistiques
```
GET /api/medical/consultations/statistiques/
```
**Réponse:**
```json
{
  "consultations_jour": 5,
  "consultations_mois": 120,
  "top_medecins": [
    {"medecin__nom": "Martin", "medecin__prenom": "Sophie", "total": 45}
  ],
  "motifs_frequents": [
    {"motif": "Consultation de routine", "total": 30}
  ],
  "total": 500
}
```

## 📱 Frontend Flutter

### Installation
```yaml
# pubspec.yaml
dependencies:
  http: ^1.1.0
  intl: ^0.18.0
```

### Configuration
```dart
// consultation_service.dart
ConsultationService.setToken('votre_token_jwt');
```

### Utilisation

#### Charger les consultations
```dart
final consultations = await ConsultationService.getConsultations();
```

#### Créer une consultation
```dart
await ConsultationService.createConsultation(
  patientId: 5,
  medecinId: 2,
  dateConsultation: DateTime.now(),
  motif: 'Consultation de routine',
  diagnosticPrincipal: 'RAS',
  notes: 'Patient en bonne santé',
);
```

#### Mettre à jour
```dart
await ConsultationService.updateConsultation(
  1,
  diagnosticPrincipal: 'Grippe',
  notes: 'Repos recommandé',
);
```

### Écran Flutter
```dart
// Dans votre main.dart
MaterialApp(
  routes: {
    '/consultations': (context) => ConsultationsScreen(),
  },
)
```

## 🚀 Démarrage

### Backend
```bash
cd trimed_backend
python manage.py runserver 0.0.0.0:8000
```

### Flutter
```bash
cd trimed_app
flutter run
```

## 📊 Fonctionnalités

### Backend
- ✅ CRUD complet des consultations
- ✅ Filtrage par date, patient, médecin
- ✅ Consultations du jour
- ✅ Historique patient
- ✅ Statistiques
- ✅ Permissions par rôle

### Flutter
- ✅ Liste des consultations
- ✅ Création de consultation
- ✅ Modification de consultation
- ✅ Détails de consultation
- ✅ Rafraîchissement
- ✅ Gestion des erreurs

## 🔐 Sécurité

- Authentification JWT requise
- Filtrage par tenant automatique
- Permissions basées sur les rôles
- Validation des données

## 📝 Prochaines étapes

1. Ajouter la sélection de patient/médecin dans Flutter
2. Implémenter la recherche
3. Ajouter les filtres de date
4. Créer un dashboard de statistiques
5. Ajouter l'export PDF des consultations

Votre application de consultation est maintenant complète et fonctionnelle !