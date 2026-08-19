# po1337nomial-revenge solution
### Author: kyc

We can get 1337 outputs of Python MT19937's RNG, but scrambled. We need to
determine their original order. If we can do this, we can use standard methods
to determine the private MT19937 state and predict future bytes, for example
with https://github.com/tna0y/Python-random-module-cracker.

To unscramble the outputs, we note that there is an XOR relationship between
terms a_i, a_{i+396}, and a_{i+623}, from the MT19937 twist. So we can find
which triplets of numbers satisfy this XOR relationship, and with good
probability they will be at positions i, i+396, and i+623 for some i.

So with good probability, we will get 1337+1-624 relationships: (0, 396, 623),
(1, 397, 624), ... (1337-624, 1337-228, 1337-1), although we don't know which
is which.

But we can repeatedly filter down the possibilities. For example, the numbers
corresponding to the first 396 MT19937 outputs must only belong in one of the
relationships. Then that reduces the possibilities for the other numbers as
well. See the solver for precise details on the implementation.

Flag: `L3AK{19937_bottles_of_beer_on_the_wall}`
