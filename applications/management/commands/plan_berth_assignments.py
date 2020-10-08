import numpy as np

from django.db import connection, transaction
from django.core.management import BaseCommand, CommandError
from scipy.optimize import linear_sum_assignment

from applications.models import BerthAssignmentPlan

_fetch_application_data_sql = """
            WITH available_berth AS 
            (
                SELECT * FROM resources_berth
                WHERE 
                    is_active = TRUE
                    AND
                    (
                        SELECT COUNT(*) FROM leases_berthlease
                        WHERE 
                            leases_berthlease.berth_id = resources_berth.id
                            AND
                            leases_berthlease.status <> 'expired'
                    ) = 0
            )
            SELECT
                application.id::varchar AS application_id,
                ARRAY_AGG(berth.id::varchar) AS berth_ids,
                ARRAY_AGG(harbor_choice.priority) AS priorities
            FROM
                applications_berthapplication AS application
                INNER JOIN applications_harborchoice AS harbor_choice
                    ON application.id = harbor_choice.application_id
                INNER JOIN harbors_harbor AS harbor_summary_data
                    ON harbor_choice.harbor_id = harbor_summary_data.id
                INNER JOIN resources_harbor AS harbor
                    ON harbor_summary_data.servicemap_id = harbor.servicemap_id
                INNER JOIN resources_pier AS pier
                    ON harbor.id = pier.harbor_id
                INNER JOIN available_berth AS berth
                    ON berth.pier_id = pier.id
            GROUP BY application.id
            ORDER BY application.created_at ASC
            LIMIT (SELECT COUNT(*) FROM available_berth)
            """


def _get_cost_matrix(row_data):
    application_id_lookup = [row[0] for row in row_data]
    berth_id_lookup = list(set().union(*[row[1] for row in row_data]))
    berth_id_reverse_lookup = dict((berth_id, index) for index, berth_id in enumerate(berth_id_lookup))

    cost_matrix = np.zeros([len(application_id_lookup), len(berth_id_lookup)])

    def scale_priority(priority):
        """
        As we're solving the assignment as a minimization problem,
        the highest priority application -> berth connections should have the smallest
        cost value. As we want to omit from consideration nonexistent application -> berth
        connections with zero values the priorities are mapped s.t.
        (1, ..., 10) -> (-10, ..., -1)

        A more sophisticated scaling function could be used here to boost the chances of users
        getting their top priority picks based on some criteria.
        """
        return priority - 11

    for application_index, row in enumerate(row_data):
        for berth_id, priority in zip(row[1], row[2]):
            berth_index = berth_id_reverse_lookup[berth_id]
            cost_matrix[application_index, berth_index] = scale_priority(priority)

    return cost_matrix, application_id_lookup, berth_id_lookup


def _get_assignments(row_data):
    cost_matrix, application_id_lookup, berth_id_lookup = _get_cost_matrix(row_data)
    application_indices, berth_indices = linear_sum_assignment(cost_matrix)
    return [(application_id_lookup[application_index], berth_id_lookup[berth_index])
            for application_index, berth_index in zip(application_indices, berth_indices)]


def _save_assignments(assignments):
    for assignment in assignments:
        application_id, berth_id = assignment
        BerthAssignmentPlan.objects.create(application_id=application_id, berth_id=berth_id).save()


def _reset_assignments():
    BerthAssignmentPlan.objects.all().delete()


class Command(BaseCommand):
    help = "Automatically find berth assignments for berth applications"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                _reset_assignments()

                with connection.cursor() as cursor:
                    cursor.execute(_fetch_application_data_sql)
                    row_data = cursor.fetchall()

                assignments = _get_assignments(row_data)
                _save_assignments(assignments)
        except Exception as e:
            raise CommandError("Assignment failed. Raised exception: %s" % e)

        self.stdout.write(self.style.SUCCESS("Done! Planned %i berth assignments." % len(assignments)))
