def moments_close_enough(t1, t2):
    return (t1 - t2).total_seconds() < 0.1
