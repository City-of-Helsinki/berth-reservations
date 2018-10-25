from csv import DictWriter


def export_reservations_as_csv(reservations, stream):
    fieldnames = [
        'first_name',
        'last_name',
        'email',
        'data'
    ]
    writer = DictWriter(stream, fieldnames=fieldnames)
    writer.writer.writerow(['sep=,'])
    writer.writeheader()
    for reservation in reservations:
        writer.writerow({
            'first_name': reservation.first_name,
            'last_name': reservation.last_name,
            'email': reservation.email,
            'data': reservation.data
        })
    return stream
