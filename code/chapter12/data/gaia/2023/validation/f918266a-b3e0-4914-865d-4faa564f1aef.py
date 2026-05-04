from random import randint
import time

class UhOh(Exception):
    pass

class Hmm:
    def __init__(self):
        self.value = randint(-100, 100)

    def Yeah(self):
        if self.value == 0:
            return True
        else:
            raise UhOh()

def Okay():
    while True:
        yield Hmm()

def keep_trying(go, first_try=True):
    maybe = next(go)
    try:
        if maybe.Yeah():
            return maybe.value
    except UhOh:
        if first_try:
            print("Working...")
            print("Please wait patiently...")
        time.sleep(0.1)
        return keep_trying(go, first_try=False)

if __name__ == "__main__":
    go = Okay()
    print(f"{keep_trying(go)}")
