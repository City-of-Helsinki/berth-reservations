import graphene
from django.db.models import QuerySet

from users.utils import is_customer


def update_object(instance, input):
    if not input:
        return
    for k, v in input.items():
        setattr(instance, k, v)
    instance.save()


class CountConnection(graphene.Connection):
    class Meta:
        abstract = True

    count = graphene.Int(
        description="Count of nodes on this connection with filters applied",
        required=True,
    )
    total_count = graphene.Int(
        description="Total count of nodes on this connection regardless of filters",
        required=True,
    )

    def resolve_count(self, info):
        if isinstance(self.iterable, QuerySet):
            return self.iterable.distinct().count()

        return len(set(self.iterable))

    def resolve_total_count(self, info, **kwargs):
        if is_customer(info.context.user):
            # If the user querying for the total is a customer (i.e. not an authorized admin),
            # we only show the items available for them, not the whole count
            return self.resolve_count(info)

        if isinstance(self.iterable, QuerySet):
            return self.iterable.model.objects.count()

        # Because the DataLoader patter returns only a list of items rather than a QuerySet,
        # it's not possible to get the model from the iterable, so we try to get the model based
        # on the connection node.
        if model := getattr(self._meta.node._meta, "model", None):
            return model.objects.count()

        return len(self.iterable)
