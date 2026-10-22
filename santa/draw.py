import random


def make_pairs(people):
    """Return a list of (giver, giftee) pairs for everyone in people.

    The people are shuffled into one circle and each person gives to the
    next one, the last person gives to the first. So nobody gets themselves,
    and with 3 or more people nobody is paired back with their own giver.
    """
    people = list(people)
    random.shuffle(people)
    return [(people[i], people[(i + 1) % len(people)]) for i in range(len(people))]
