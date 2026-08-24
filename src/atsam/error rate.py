#!/bin/bash
import math

def integerError(input: float) -> float:
    return abs((1 - (input / math.floor(input)))*100)

def funcA(boudrate: int) -> float:
    return integerError(45_000_000.0 / (16*boudrate))

def funcB(boudrate: int) -> float:
    return integerError(150_000_000.0 / (16*boudrate))

def combined_error(b: int, wA: float = 1.0, wB: float = 1.0) -> float:
    return wA * funcA(b) + wB * funcB(b)

def find_best_boudrate(b_min: int, b_max: int, wA: float = 1.0, wB: float = 1.0):
    best_b = None
    best_val = float("inf")

    for b in range(b_min, b_max + 1):
        val = combined_error(b, wA=wA, wB=wB)
        if val < best_val:
            best_val = val
            best_b = b

    return best_b, best_val, funcA(best_b), funcB(best_b)

if __name__ == "__main__":
    # Choose a sensible domain for your boudrate (must be >= 1)
    b_opt, err_sum, errA, errB = find_best_boudrate(500_000, 1_000_000)

    print(f"Best boudrate:{b_opt}")
    print(f"funcA error:{errA}")
    print(f"funcB error:{errB}")
    print(f"Combined (A+B):{err_sum}")
