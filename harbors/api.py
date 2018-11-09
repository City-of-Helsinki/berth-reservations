import django_filters
from parler_rest.serializers import TranslatableModelSerializer, TranslatedFieldsField
from rest_framework import serializers, viewsets
from munigeo.api import GeoModelSerializer
from munigeo.models import Municipality

from .models import BoatType, Harbor


class TranslatedModelSerializer(TranslatableModelSerializer):
    translations = TranslatedFieldsField()

    def to_representation(self, obj):
        ret = super(TranslatedModelSerializer, self).to_representation(obj)
        if obj is None:
            return ret
        return self.translated_fields_to_representation(obj, ret)

    def translated_fields_to_representation(self, obj, ret):
        translated_fields = {}

        for lang_key, trans_dict in ret.pop('translations', {}).items():

            for field_name, translation in trans_dict.items():
                if field_name not in translated_fields:
                    translated_fields[field_name] = {lang_key: translation}
                else:
                    translated_fields[field_name].update({lang_key: translation})

        ret.update(translated_fields)

        return ret


class BoatTypeSerializer(TranslatedModelSerializer):

    class Meta:
        model = BoatType
        fields = ['identifier', 'translations']


class BoatTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BoatType.objects.all()
    serializer_class = BoatTypeSerializer


class MunicipalityRelatedField(TranslatedModelSerializer):
    """
    Fetch Municipality's translations for `name` field and
    display them at the endpoint in the following way:

    "municipality": {
        "fi": "Helsinki",
        "sv": "Helsingfors"
    }

    """

    class Meta:
        model = Municipality
        fields = ['translations']

    def to_representation(self, obj):
        ret = super(MunicipalityRelatedField, self).to_representation(obj)
        return ret['name']


class HarborSerializer(TranslatedModelSerializer, GeoModelSerializer):
    suitable_boat_types = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='identifier'
    )
    municipality = MunicipalityRelatedField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Harbor
        exclude = ['id', 'servicemap_id', 'image_file', 'image_link', 'maximum_depth']

    def get_image(self, obj):
        """
        Image_file field has higher priority.
        We check image_link field only if there is no image_file.
        """
        if obj.image_file:
            return obj.image_file
        elif obj.image_link:
            return obj.image_link
        else:
            return None


class HarborFilter(django_filters.FilterSet):
    suitable_boat_types = django_filters.CharFilter(
        field_name='suitable_boat_types__identifier'
    )
    maximum_width = django_filters.NumberFilter(
        lookup_expr='gte'
    )
    maximum_length = django_filters.NumberFilter(
        lookup_expr='gte'
    )

    class Meta:
        model = Harbor
        fields = (
            'mooring', 'electricity', 'water', 'waste_collection', 'gate', 'lighting',
            'suitable_boat_types', 'maximum_width', 'maximum_length'
        )


class HarborViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Harbor.objects.all()
    serializer_class = HarborSerializer
    filter_class = HarborFilter
