from utils.relay import to_global_id


def parse_invoicing_result(node_type):
    """Wrapper function to allow reusing the parse function with different Node types"""

    def parse_to_dict(object):
        """Util function to parse a dict of {"UUID": "message"} into {"id": "UUID", "error": "message"} """
        id, error = list(object.items())[0]
        return {"id": to_global_id(node_type, id), "error": error}

    return parse_to_dict
