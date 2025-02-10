"""
Name: timer_decorator.py
Purpose: decorator func to time how long a function takes to run


Author: Darren Conly
Last Updated: Feb 2025
Updated by: 
Copyright:   (c) SACOG
Python Version: 3.x
"""

def func_timer(input_func):
    from time import perf_counter

    def wrap_func(*args, **kwargs): 
        t1 = perf_counter() 
        result = input_func(*args, **kwargs) 
        t2 = perf_counter() 
        print(f'Function {input_func.__name__!r} executed in {(t2-t1):.1f}s') 
        return result 
    
    return wrap_func 

@func_timer
def test_func(p1, p2):
    print(p1, p2)
    sqsum = 0
    for i in range(1000):
        sqsum += i*i

    return sqsum


if __name__ == '__main__':
    test_func('foo', 'bar')