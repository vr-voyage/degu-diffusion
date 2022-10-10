class Helpers:
    # I hate the ValueError stupidity from int()/float()
    # This makes it very hard to one-line parsing
    # Hence 4 methods that allow for quick parsing and
    # default fallbacks when parsing fail.

    @staticmethod
    def to_int(value_string:str, fallback:int):
        value:int = fallback
        try:
            value = int(value_string)
        except ValueError:
            value = fallback
        return value

    @staticmethod
    def to_int_clamped(value_string:str, fallback:int, min_value:int, max_value:int):
        value:int = Helpers.to_int(value_string, fallback)
        value = min(max_value, value)
        value = max(min_value, value)
        return value

    @staticmethod
    def to_float(value_string:str, fallback:float):
        value:float = fallback
        try:
            value = float(value_string)
        except:
            value = fallback
        return value

    @staticmethod
    def to_float_clamped(value_string:str, fallback:float, min_value:float, max_value:float):
        value:float = Helpers.to_float(value_string, fallback)
        value = min(max_value,value)
        value = max(min_value,value)
        return value
