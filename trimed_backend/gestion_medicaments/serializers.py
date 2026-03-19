# serializers.py
from rest_framework import serializers
from .models import MedicamentCategorie, Medicament

class MedicamentCategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicamentCategorie
        fields = '__all__'
        read_only_fields = ('categorie_id', 'created_at', 'updated_at')
    
    def validate_nom(self, value):
        """Vérifier l'unicité du nom dans le tenant"""
        tenant = self.context['request'].user.hopital
        if MedicamentCategorie.objects.filter(tenant=tenant, nom=value).exists():
            raise serializers.ValidationError("Cette catégorie existe déjà dans cet hôpital")
        return value

class MedicamentSerializer(serializers.ModelSerializer):
    categorie_detail = MedicamentCategorieSerializer(source='categorie', read_only=True)
    categorie_id = serializers.PrimaryKeyRelatedField(
        queryset=MedicamentCategorie.objects.all(),
        source='categorie',
        write_only=True,
        required=False,
        allow_null=True
    )
    besoin_reapprovisionnement = serializers.ReadOnlyField()
    
    class Meta:
        model = Medicament
        fields = [
            'medicament_id', 'tenant', 'nom', 'forme_pharmaceutique',
            'dosage_standard', 'categorie', 'categorie_id', 'categorie_detail',
            'code_atc', 'dci', 'description', 'stock_actuel', 'stock_minimum',
            'prix_unitaire', 'necessite_ordonnance', 'actif',
            'besoin_reapprovisionnement', 'created_at', 'updated_at'
        ]
        read_only_fields = ('medicament_id', 'created_at', 'updated_at')
    
    def validate_stock_actuel(self, value):
        if value < 0:
            raise serializers.ValidationError("Le stock ne peut pas être négatif")
        return value
    
    def validate_stock_minimum(self, value):
        if value < 0:
            raise serializers.ValidationError("Le stock minimum ne peut pas être négatif")
        return value
    
    def validate_prix_unitaire(self, value):
        if value and value < 0:
            raise serializers.ValidationError("Le prix ne peut pas être négatif")
        return value

class MedicamentListSerializer(serializers.ModelSerializer):
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    besoin_reapprovisionnement = serializers.ReadOnlyField()
    
    class Meta:
        model = Medicament
        fields = [
            'medicament_id', 'nom', 'forme_pharmaceutique',
            'dosage_standard', 'categorie_nom', 'stock_actuel',
            'stock_minimum', 'besoin_reapprovisionnement', 'actif'
        ]

class StockUpdateSerializer(serializers.Serializer):
    """Serializer pour la mise à jour du stock"""
    
    quantite = serializers.IntegerField(required=True)
    operation = serializers.ChoiceField(
        choices=['ajouter', 'retirer', 'definir'],
        required=True
    )
    motif = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    def validate_quantite(self, value):
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être positive")
        return value