# A Fine Product solution
### Author: kyc

We are given 999 functions f(s) = a_i s + b_i. There are two steps to this
challenge:

1. Find a list of functions (chosen from the given 999 functions) such that
   they compose to f(s) = 2s + 1.
2. Factor n = s(2s+1)r.

For step 1: note that composing two functions f(s) = a_1 s + b_1 and
f(s) = a_2 s + b_2 will give the function f(s) = a_1 a_2 s + [some constant].
This means that in order to find a list of functions that compose to
f(s) = a*s + [some constant], for some target a, we need to find (small)
multiplicities e_i such that

Π_i (a_i)^(e_i) = a.

We can take the discrete logs of the a_i and a (mod N). Then this is equivalent
to finding small multiplicities such that

Σ_i (e_i) DLOG(a_i) = DLOG(a),

and this can be solved using lattices.
(https://magicfrank00.github.io/writeups/posts/lll-to-solve-linear-equations/
is one way to do this, although the provided solver uses Sage 10.9's built in
approximate_closest_vector.)

Using this we can find composed functions f(s) = 2s + [some constant] and
many functions f(s) = s + [some constant]. Again, we can use lattices to find
multiplicities of these functions so that they all compose to f(s) = 2s + 1.

For step 2: we can repeatedly retry until 2s + 1 is prime. Then we are given
n = s(2s+1)r for some unknown s,r. However, by Fermat's Little Theorem,

2^(2n) ≡ (2^(2s)) ^ ((2s+1)r) ≡ 1 ^ ((2s+1)r) ≡ 1 (mod 2s+1),

so 2^(2n) - 1 is divisible by 2s+1. This means that we can compute
GCD(2^(2n) - 1, n) and we will likely get 2s+1.

Flag: `L3AK{9nineNINE99_nInE9999NineNINe}`
