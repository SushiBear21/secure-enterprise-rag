GROUP_AUDIENCES = {
    "employees": {"all_employees"},
    "soc_analysts": {"all_employees", "soc_analysts"},
    "acquisition_team": {"all_employees", "acquisition_team"},
}


class AccessDenied(Exception):
    pass


def allowed_audiences(groups):
    """Accept groups from a verified identity, never from the request body."""
    if not isinstance(groups, list):
        raise AccessDenied("Group membership must be a list.")

    audiences = set()

    for group in groups:
        if not isinstance(group, str):
            raise AccessDenied("Invalid group membership.")

        audiences.update(GROUP_AUDIENCES.get(group, set()))

    if not audiences:
        raise AccessDenied("No recognized access group.")

    return sorted(audiences)