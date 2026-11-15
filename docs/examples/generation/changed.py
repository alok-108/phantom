"""Same program, but the behavior was changed."""


def total(prices):
    return sum(prices) + 1


if __name__ == "__main__":
    print(total([3, 4, 5]))
