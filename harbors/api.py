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

    class Meta:
        model = Harbor
        exclude = ['id', 'servicemap_id', 'maximum_depth']

    def to_representation(self, obj):
        """
        Combine `image_file` and `image_link` into one `image` field.
        Image_file field has higher priority.
        We check image_link field only if there is no image_file.
        """
        representation = super().to_representation(obj)

        representation['image'] = None
        if representation['image_file']:
            representation['image'] = representation['image_file']
        elif representation['image_link']:
            representation['image'] = representation['image_link']

        representation.pop('image_file')
        representation.pop('image_link')
        return representation


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
