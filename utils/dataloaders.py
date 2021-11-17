from collections import defaultdict
from typing import Type

from django.db.models import Model
from promise import Promise
from promise.dataloader import DataLoader


def model_loader(model: Type[Model]):
    class ModelLoader(DataLoader):
        def batch_load_fn(self, object_ids):
            objects = defaultdict(model)

            for object in model.objects.filter(id__in=object_ids).iterator():
                objects[object.id] = object

            return Promise.resolve([objects.get(object_id) for object_id in object_ids])

    return ModelLoader
