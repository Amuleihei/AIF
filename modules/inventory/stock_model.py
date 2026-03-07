class Stock:

    def __init__(self, name, qty=0):
        self.name = name
        self.qty = qty

    def add(self, v):
        self.qty += v

    def remove(self, v):
        self.qty -= v