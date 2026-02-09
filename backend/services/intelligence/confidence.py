class ConfidenceScoring:
    @staticmethod
    def score(projection: float, line: float) -> int:
        diff = abs(projection - line)
        if diff >= 10:
            return 95
        if diff >= 5:
            return 80
        if diff >= 3:
            return 65
        if diff >= 1:
            return 50
        return 30