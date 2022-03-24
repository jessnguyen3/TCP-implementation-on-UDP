import random

def lose_datagram(pdrop, seed):
    chance = random.random()
    print(chance)
    if (chance <= pdrop):
        return True
    return False

random.seed(5)
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
print(lose_datagram(0.5, random))
