def moments_close_enough(t1, t2):
    """
    Return True if the two times are very close to each other.

    Works around databases losing time precision.

    :param t1: Instant 1
    :param t2: Instant 2
    :return: Closeness boolean
    """
    return (t1 - t2).total_seconds() < 0.1
