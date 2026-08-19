# BabyLCG Solution
### Author: aresinheaven

Given 3 successive outputs of a Linear Congruential Generator, we can directly solve for the hidden multiplier `a` by computing the difference between consecutive outputs to eliminate the constant term `c`:
```python
a = (((s2-s1)%m) * pow((s1-s0)%m, -1, m)) % m
```
Then we can plug this back in and solve for `c` easily:
```python
c = (s2-a*s1) % m
```
Then we can solve for the key by taking the next LCG output:
```python
key = (a*s2 + c) % m
flag_int = key ^ ct
flag = long_to_bytes(flag_int).decode()
print(f'flag = {flag}')
```

Flag: `L3AK{n3v3r_trU5t_b4s1c_LCG5_frfr}`
