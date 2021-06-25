import graphene
from django.db.models import QuerySet

from users.utils import is_customer, user_has_view_permission


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
        model = None
        user = info.context.user

        if isinstance(self.iterable, QuerySet):
            model = self.iterable.model

        # Because the DataLoader patter returns only a list of items rather than a QuerySet,
        # it's not possible to get the model from the iterable, so we try to get the model based
        # on the connection node.
        elif node_model := getattr(self._meta.node._meta, "model", None):
            model = node_model

        # If the user is an admin (does have enough permissions), return the total
        # amount of objects
        if user_has_view_permission(model)(user) and model:
            return model.objects.count()

        # If it's a customer (only enough permissions for its own data)
        # only return the size of the batch returned (same as count)
        if is_customer(user):
            # If the user querying for the total is a customer (i.e. not an authorized admin),
            # we only show the items available for them, not the whole count
            return self.resolve_count(info)

        return len(self.iterable)
