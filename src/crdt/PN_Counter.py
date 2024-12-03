class PNCounter:
    def __init__(self):
        self.positive = 0  
        self.negative = 0 

    def increment(self, value=1):
        self.positive += value

    def decrement(self, value=1):
        self.negative += value

    def get_value(self):
        return self.positive - self.negative

    def merge(self, other):
        self.positive = max(self.positive, other.positive)
        self.negative = max(self.negative, other.negative)
